from across_edge.runmeta import config_fingerprint,endpoint_class
def test_metadata_redacts_endpoint_and_secret_values():
 assert endpoint_class('https'+chr(58)+'//'+'u'+chr(58)+'p'+'@example.com/rpc?key=x')=='https://example.com';a=config_fingerprint({'API_KEY':'secret','x':1});b=config_fingerprint({'API_KEY':'other','x':1});assert a==b
