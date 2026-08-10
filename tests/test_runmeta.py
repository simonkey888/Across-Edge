from across_edge.runmeta import RunMetadata,config_fingerprint,endpoint_class
def test_metadata_redacts_endpoint_and_secret_values():
 assert endpoint_class('https'+chr(58)+'//'+'u'+chr(58)+'p'+'@example.com/rpc?key=x')=='https://example.com';assert config_fingerprint({'API_KEY':'secret','x':1})==config_fingerprint({'API_KEY':'other','x':1});m=RunMetadata('r',our_sha='a',upstream_sha='b',config={},routes=[],endpoints=[]);assert m.payload['schema_version']==3
