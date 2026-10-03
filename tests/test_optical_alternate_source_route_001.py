import ast
import copy
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import optical_alternate_catalog_001 as catalog
import optical_alternate_intake_001 as intake
import run_m2_optical_alternate_source_route_001 as route
from test_landsat9_visual_route_completion_001 import fixture_bytes, fixture_groups
from test_landsat_l2_grouped_mtl_integrity_002 import write_tar

GEOMETRY = {"type": "Polygon", "coordinates": [[[84, 27], [86, 27], [86, 29], [84, 29], [84, 27]]]}
GEOMETRIES = {key: {"type": "Polygon", "coordinates": [[[84.5, 27.5], [85, 27.5], [85, 28], [84.5, 28], [84.5, 27.5]]]}
              for key in catalog.AOIS}


def feature(sensor=8, date="20260803", cloud=12):
    from datetime import datetime
    dt = datetime.strptime(date, "%Y%m%d")
    product = f"LC0{sensor}_L2SP_141040_{date}_{date}_02_T1"
    return {"type": "Feature", "collection": catalog.COLLECTION, "id": product + "_SR", "geometry": copy.deepcopy(GEOMETRY),
            "properties": {"platform": f"landsat-{sensor}", "datetime": dt.strftime("%Y-%m-%dT04:35:12.123456Z"),
                           "eo:cloud_cover": cloud, "landsat:wrs_path": 141, "landsat:wrs_row": 40,
                           "landsat:collection_number": "02", "landsat:collection_category": "T1",
                           "landsat:processing_level": "L2SP", "landsat:scene_id": f"LC{sensor}141040{dt.strftime('%Y%j')}LGN00"}}


def disposition(item, role):
    return catalog.item_disposition(item, item["properties"]["platform"], role, GEOMETRIES)


def locked_pair(sensor=8):
    rows = [disposition(feature(sensor), "before"), disposition(feature(sensor, "20260904", 11), "after")]
    return catalog.rank_pairs(rows, True)[0]


class CatalogPolicyTests(unittest.TestCase):
    def test_both_sensor_identities_and_footprints(self):
        for sensor in (8, 9):
            row = disposition(feature(sensor), "before")
            self.assertTrue(row["eligible"])
            self.assertTrue(all(row["catalog_focus_containment"].values()))

    def test_official_usgs_platform_and_zero_padded_wrs_serialization(self):
        for sensor in (8,9):
            item=feature(sensor)
            item['properties'].update({'platform':f'LANDSAT_{sensor}','landsat:wrs_path':'141','landsat:wrs_row':'040'})
            row=catalog.item_disposition(item,f'landsat-{sensor}','before',GEOMETRIES)
            self.assertTrue(row['eligible'])
            self.assertEqual(row['platform'],f'landsat-{sensor}')
            self.assertEqual(row['reported_catalog_platform'],f'LANDSAT_{sensor}')
            item['properties']['landsat:wrs_row']='041'
            self.assertFalse(catalog.item_disposition(item,f'landsat-{sensor}','before',GEOMETRIES)['eligible'])

    def test_required_identity_fields_and_wrong_values_are_ineligible(self):
        for key in ("platform", "datetime", "landsat:scene_id", "landsat:wrs_path", "landsat:wrs_row",
                    "landsat:collection_number", "landsat:collection_category"):
            for bad in (None, "unexpected", True):
                item = feature(); item["properties"][key] = bad
                self.assertFalse(catalog.item_disposition(item, "landsat-8", "before", GEOMETRIES)["eligible"], (key, bad))

    def test_cloud_unknown_nonfinite_boolean_and_out_of_range_never_zeroed(self):
        for cloud in (None, float("nan"), float("inf"), True, -1, 101, "0"):
            item = feature(cloud=cloud)
            row = disposition(item, "before")
            self.assertFalse(row["eligible"])
            self.assertIsNone(row["eo_cloud_cover"])

    def test_product_datetime_scene_and_independent_product_disagreement(self):
        for field, bad in (("datetime", "2026-08-04T04:35:12Z"), ("landsat:product_id", "LC08_L2SP_141040_20260804_20260804_02_T1"),
                           ("landsat:scene_id", "LC91410402026215LGN00"), ("landsat:processing_level", "L2SR")):
            item = feature(); item["properties"][field] = bad
            self.assertFalse(disposition(item, "before")["eligible"])

    def test_fixed_windows_and_event_day_exclusions(self):
        for date, role in (("20260726", "before"), ("20260826", "before"), ("20260826", "after"), ("20260926", "after")):
            self.assertFalse(disposition(feature(date=date), role)["eligible"])
        item = feature(9, "20260810")
        item["id"] = "LC09_L2SP_141040_20260810_20260811_02_T1_SR"
        self.assertIn("known_terminal_product_never_requeue", disposition(item, "before")["reasons"])

    def test_invalid_and_partial_geometry_retained_not_selected(self):
        for geometry in (None, {"type": "Polygon", "coordinates": []},
                         {"type": "Polygon", "coordinates": [[[84,27],[84.1,27],[84.1,27.1],[84,27.1],[84,27]]]}):
            item = feature(); item["geometry"] = geometry
            self.assertFalse(disposition(item, "before")["eligible"])

    def test_complete_same_sensor_deterministic_rank_and_two_pair_cap(self):
        rows = [disposition(feature(8, "20260803", 4), "before"), disposition(feature(8, "20260819", 4), "before"),
                disposition(feature(8, "20260904", 6), "after"), disposition(feature(9, "20260802", 5), "before"),
                disposition(feature(9, "20260903", 6), "after")]
        pairs = catalog.rank_pairs(rows, True)
        self.assertEqual(len(pairs), 2)
        self.assertIn("20260819", pairs[0]["before"]["product_id"])
        for pair in pairs:
            self.assertEqual(pair["before"]["platform"], pair["after"]["platform"])
        self.assertEqual(pairs, catalog.rank_pairs(list(reversed(rows)), True))
        with self.assertRaisesRegex(catalog.PolicyStop, "incomplete"):
            catalog.rank_pairs(rows, False)

    def test_duplicate_identity_conflict_hard_stops(self):
        a = disposition(feature(), "before"); b = copy.deepcopy(a); b["eo_cloud_cover"] = 99
        with self.assertRaisesRegex(catalog.PolicyStop, "duplicate_catalog"):
            catalog.rank_pairs([a,b], True)

    def ledger(self, transport):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        return catalog.MetadataLedger(Path(temp.name)/"attempt", transport=transport, sleeper=lambda _: None)

    def test_fixed_order_query_and_complete_pagination(self):
        calls = []
        pages = [dict(type="FeatureCollection", features=[], links=[], numberMatched=0) for _ in range(4)]
        def http(method, url, body):
            calls.append((method, url, body))
            return 200,"application/json",json.dumps(pages.pop(0)).encode()
        ledger = self.ledger(http)
        out = catalog.discover(ledger, GEOMETRIES)
        self.assertEqual([(q["platform"],q["role"]) for q in out["queries"]], list(catalog.ORDER))
        self.assertEqual(ledger.total, 4)
        self.assertTrue(out["complete"])
        self.assertTrue(all((ledger.path/f"request-{n:02d}-intent.json").exists() for n in range(1,5)))
        from urllib.parse import parse_qs,urlsplit
        for call,(sensor,role) in zip(calls,catalog.ORDER):
            query=json.loads(parse_qs(urlsplit(call[1]).query)['query'][0])
            self.assertEqual(query,{'platform':{'eq':catalog.PROVIDER_PLATFORM[sensor]}})

    def test_pagination_cycle_wrong_host_missing_count_and_page_caps_stop(self):
        for mode in ("wrong_host", "count", "overfull", "unproven"):
            page = {"type":"FeatureCollection","features":[],"links":[]}
            if mode == "wrong_host": page["links"]=[{"rel":"next","href":"https://example.com/search"}]
            if mode == "count": page["numberMatched"]=1
            if mode == "overfull": page["features"]=[feature()]*101
            if mode == "unproven": page["features"]=[feature()]*100
            ledger = self.ledger(lambda *args: (200,"application/json",json.dumps(page).encode()))
            with self.assertRaises(catalog.PolicyStop): catalog.discover(ledger,GEOMETRIES)

    def test_complete_count_ignores_superfluous_cursor_and_preserved_page_is_not_replayed(self):
        item=feature();item['properties']['platform']='LANDSAT_8'
        page={'type':'FeatureCollection','features':[item],'numberMatched':1,'numberReturned':1,
              'links':[{'rel':'next','method':'GET','href':catalog.SEARCH+'?next=cursor'}]}
        calls=[]
        empty={'type':'FeatureCollection','features':[],'numberMatched':0,'numberReturned':0,'links':[]}
        ledger=self.ledger(lambda *args:(calls.append(args) or (200,'application/json',json.dumps(empty).encode())))
        out=catalog.discover(ledger,GEOMETRIES,preserved_complete_pages={('landsat-8','before'):page})
        self.assertEqual(ledger.total,3)
        self.assertEqual(len(calls),3)
        self.assertEqual(out['queries'][0]['features_returned'],1)
        self.assertTrue(out['dispositions'][0]['eligible'])
        self.assertTrue(out['queries'][0]['uses_exact_preserved_complete_response_without_request_replay'])

    def test_budgets_and_response_caps_before_transport(self):
        ledger = self.ledger(lambda *args: (200,"application/json",b'{}'))
        for _ in range(8): ledger.request("search", catalog.SEARCH)
        with self.assertRaisesRegex(catalog.PolicyStop,"budget"): ledger.request("search",catalog.SEARCH)
        self.assertEqual(ledger.total,8)
        ledger = self.ledger(lambda *args: (200,"application/json",b' '*(catalog.MAX_RESPONSE+1)))
        with self.assertRaisesRegex(catalog.PolicyStop,"size_cap"): ledger.request("root",catalog.CATALOG)

    def test_only_transient_recovery_and_no_denial_or_schema_retry(self):
        for status in (401,403,404,302,200):
            calls=[]
            ledger=self.ledger(lambda *args:(calls.append(args) or (status,"application/json",b'invalid')))
            with self.assertRaises(catalog.PolicyStop): ledger.request("root",catalog.CATALOG)
            self.assertEqual(len(calls),1)
        replies=[(503,"application/json",b'{}'),(200,"application/json",b'{}')]
        ledger=self.ledger(lambda *args:replies.pop(0))
        ledger.request("root",catalog.CATALOG)
        self.assertEqual((ledger.total,ledger.counts["recovery"]),(2,1))

    def test_recovery_exhaustion_preserves_two_attempts(self):
        ledger=self.ledger(lambda *args:(429,"application/json",b'{}'))
        with self.assertRaisesRegex(catalog.PolicyStop,"exhausted"): ledger.request("root",catalog.CATALOG)
        self.assertEqual(ledger.total,2)
        self.assertEqual(len(list(ledger.path.glob('*outcome.json'))),2)

    def test_distinct_mechanical_attempt_inherits_not_resets_budgets(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        seed={'counts':{'root':1,'rights':1,'search':4,'detail':0,'recovery':0},'total':6,'outcomes':[],'terminal_sha256':'a'*64}
        ledger=catalog.MetadataLedger(Path(temp.name)/'new',transport=lambda *args:(200,'application/json',b'{}'),seed=seed)
        for _ in range(4):ledger.request('search',catalog.SEARCH)
        self.assertEqual((ledger.total,ledger.counts['search']),(10,8))
        with self.assertRaisesRegex(catalog.PolicyStop,'budget'):ledger.request('search',catalog.SEARCH)
        self.assertTrue((ledger.path/'request-07-intent.json').exists())
        self.assertFalse((ledger.path/'request-01-intent.json').exists())

    def test_url_assets_credentials_unknown_origins_never_sent(self):
        ledger=self.ledger(lambda *args:self.fail("unexpected network"))
        for url in ("http://landsatlook.usgs.gov/stac-server/search", "https://x:secret@landsatlook.usgs.gov/stac-server/search",
                    "https://landsatlook.usgs.gov/stac-server/assets/a.tif", "https://landsatlook.usgs.gov.evil.example/stac-server/search"):
            with self.assertRaises(catalog.PolicyStop): ledger.request("search",url)
        self.assertEqual(ledger.total,0)

    def test_pagination_cannot_widen_window_or_duplicate_query(self):
        ledger=self.ledger(lambda *args:self.fail('unexpected network'))
        ledger.query_context={'datetime':'fixed'}
        for query in ('datetime=changed','datetime=fixed&datetime=changed','datetime=fixed&asset=band.tif'):
            with self.assertRaises((catalog.PolicyStop,ValueError)):ledger.request('search',catalog.SEARCH+'?'+query)
        self.assertEqual(ledger.total,0)

    def test_all_per_kind_and_total_caps(self):
        for kind,url,cap in (('root',catalog.CATALOG,2),('rights',catalog.RIGHTS,2),
                             ('detail',catalog.CATALOG+'collections/'+catalog.COLLECTION+'/items/'+feature()['id'],4)):
            ledger=self.ledger(lambda *args:(200,'text/html' if kind=='rights' else 'application/json',b'{}'))
            for _ in range(cap):ledger.request(kind,url)
            with self.assertRaisesRegex(catalog.PolicyStop,'budget'):ledger.request(kind,url)
        ledger=self.ledger(lambda *args:self.fail('unexpected network'));ledger.total=18
        with self.assertRaisesRegex(catalog.PolicyStop,'budget'):ledger.request('search',catalog.SEARCH)

    def test_duplicate_json_keys_and_attempt_replay_stop(self):
        ledger=self.ledger(lambda *args:(200,'application/json',b'{"type":"Catalog","type":"Other"}'))
        with self.assertRaisesRegex(catalog.PolicyStop,'json_invalid'):ledger.request('root',catalog.CATALOG)
        with self.assertRaisesRegex(catalog.PolicyStop,'already_reserved'):catalog.MetadataLedger(ledger.path)

    def test_supervisor_interruption_preserves_terminal_no_content(self):
        ledger=self.ledger(lambda *args:self.fail('unexpected network'))
        working=ledger.path/'worker-test';working.mkdir()
        gate=working/'gate.json'
        catalog.write_new(gate,{'status':'pass_final_no_content_preflight','recovery_approval_sha256':catalog.APPROVAL_SHA,
                               'recovery_attempt_root_absent':True,'independent_event_roots_absent':True,
                               'implementation_public_ci_commit':'a'*40,'implementation_public_ci_run_id':'12345678'})
        roots=tuple(working/name for name in ('attempt','events','fallback'))
        def worker(_):raise OSError('secret-sentinel-not-to-be-retained')
        with patch.object(route,'validate_gate',return_value=None):
            result=route.supervise_stage(gate,roots=roots,worker=worker)
        self.assertEqual(result['worker_invocations'],1)
        self.assertFalse(roots[0].exists())
        output=''.join(p.read_text(encoding='utf-8') for root in roots[1:] for p in root.glob('*.json'))
        self.assertNotIn('secret-sentinel',output)
        self.assertTrue((roots[1]/'terminal.json').exists())
        self.assertTrue((roots[1]/'cleanup.json').exists() or (roots[2]/'cleanup.json').exists())

    def test_detail_drift_stops_before_selection_lock(self):
        b,a=feature(),feature(date="20260904")
        rows=[disposition(b,"before"),disposition(a,"after")]
        bad=copy.deepcopy(b); bad["properties"]["eo:cloud_cover"]=99
        ledger=self.ledger(lambda *args:(200,"application/json",json.dumps(bad).encode()))
        with self.assertRaisesRegex(catalog.PolicyStop,"detail_identity"): catalog.lock_selection(ledger,{"complete":True,"dispositions":rows},GEOMETRIES)
        self.assertTrue((ledger.path/'inventory.json').exists())
        self.assertFalse((ledger.path/'selection-manifest.json').exists())


class IntakeAndVisualRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.data=self.root/'data';self.data.mkdir();self.downloads=self.root/'downloads';self.downloads.mkdir()
        self.pair=locked_pair()
        self.selection=self.root/'selection.json'
        catalog.write_new(self.selection,{"status":"pass_complete_fixed_policy_selection_locked","approval_sha256":catalog.APPROVAL_SHA,"pairs":[self.pair]})
        self.gate={"status":"pass_final_no_content_preflight","approval_sha256":catalog.APPROVAL_SHA}
        self.rights={"pass_unchanged_usgs_rights_and_exact_full_bundle_option":True}

    def reserve(self,role="before"):
        with patch.object(intake.shutil,"disk_usage",return_value=type('Space',(),{'free':intake.MIN_FREE})()):
            return intake.reserve(self.data,self.downloads,self.selection,1,role,self.gate,self.rights)

    def test_preexisting_or_ambiguous_browser_files_stop(self):
        product=self.pair['before']['product_id']
        for name in (product+'.tar',product+' (1).tar',product+'.tar.crdownload'):
            p=self.downloads/name;p.write_bytes(b'x')
            with self.assertRaisesRegex(catalog.PolicyStop,"preexists"):self.reserve()
            p.unlink()
        with self.assertRaisesRegex(catalog.PolicyStop,"ambiguous"):
            intake.candidate({product+'.tar':{'bytes':10},product+' (1).tar':{'bytes':10}},product)

    def test_fixed_order_and_nonterminal_activation_prevent_replay(self):
        with self.assertRaisesRegex(catalog.PolicyStop,"before_source"):self.reserve('after')
        attempt,_,_=self.reserve()
        with self.assertRaisesRegex(catalog.PolicyStop,"not_terminal"):self.reserve()
        self.assertTrue((attempt/'intent.json').exists())

    def test_one_synthetic_container_promotion_and_immutable_terminal(self):
        attempt,staging,destination=self.reserve()
        source=self.pair['before'];product=source['product_id'];scene=source['scene_id']
        text,xml=fixture_bytes(fixture_groups(product,scene))
        items=[(product+s,text if s=='_MTL.txt' else xml if s=='_MTL.xml' else b'synthetic-not-tiff') for s in metadata_suffixes()]
        write_tar(self.downloads/(product+'.tar'),items)
        tick=[0]
        def pause(_):tick[0]+=1
        result=intake.finish(attempt,staging,destination,self.downloads,clock=lambda:tick[0],pause=pause,stable=2,limit=10)
        self.assertEqual(result['status'],'pass_container_only_no_replace_custody')
        self.assertTrue(destination.is_file())
        with self.assertRaisesRegex(catalog.PolicyStop,'consumed'):intake.finish(attempt,staging,destination,self.downloads)

    def test_received_budget_includes_partials_and_failed_requests(self):
        attempts=self.root/'attempts';p=attempts/'activation-001';p.mkdir(parents=True)
        catalog.write_new(p/'sample-00001.json',{'observed_received_bytes':100})
        catalog.write_new(p/'sample-00002.json',{'observed_received_bytes':120})
        q=attempts/'activation-002';q.mkdir()
        catalog.write_new(q/'sample-00001.json',{'observed_received_bytes':150})
        self.assertEqual(intake.received_bytes(attempts),270)

    def test_wrong_rights_and_outside_source_no_intent(self):
        self.rights={}
        with self.assertRaisesRegex(catalog.PolicyStop,'rights'):self.reserve()
        self.assertFalse((self.data/'.intake-staging').exists())

    def test_full_first_pair_stops_second_partial_and_full_selection(self):
        row=lambda n,full,partial:{'status':'pass_pair_visual_qa_only','rank':n,'full_both_aois':full,'qualifying_aois':['AOI-SOURCE'] if partial else []}
        self.assertEqual(route.choose_panel([row(1,True,True)],2),1)
        self.assertEqual(route.choose_panel([row(1,False,True),row(2,True,True)],2),2)
        self.assertEqual(route.choose_panel([row(1,False,True),row(2,False,True)],2),1)
        self.assertIsNone(route.choose_panel([row(1,False,False),row(2,False,False)],2))
        with self.assertRaises(catalog.PolicyStop):route.choose_panel([row(1,False,True)],2)
        with self.assertRaises(catalog.PolicyStop):route.choose_panel([row(1,True,True),row(2,True,True)],2)
        with self.assertRaises(catalog.PolicyStop):route.choose_panel([{'status':'blocked_terminal_no_retry','rank':1}],2)

    def test_frozen_panel_pixel_functions_are_exact_ast_equivalents(self):
        scripts=Path(route.__file__).parent
        def nodes(path):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
        old,new=nodes(scripts/'landsat9_visual_panel_arcgis_001.py'),nodes(scripts/'optical_alternate_panel_arcgis_001.py')
        for key in ('_panel_arrays','_save_raster','rect','digest'):
            self.assertEqual(old[key],new[key])

    def test_l8_and_l9_grouped_metadata_unchanged_scale(self):
        import landsat9_grouped_visual_metadata_001 as adapter
        for sensor in (8,9):
            source=locked_pair(sensor)['before']
            result=adapter.inspect(*fixture_bytes(fixture_groups(source['product_id'],source['scene_id'])),source['product_id'],source['scene_id'])
            self.assertEqual(result['reflectance_mult'],.0000275)
            self.assertEqual(result['reflectance_add'],-.2)


def metadata_suffixes():
    from landsat_l2_grouped_mtl_integrity_002 import REQUIRED_SUFFIXES
    return REQUIRED_SUFFIXES


if __name__ == '__main__':unittest.main()
