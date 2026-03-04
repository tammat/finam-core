from finam_core.gateway.finam_gateway import FinamGateway

gw = FinamGateway()

assets = gw.get_assets()

print(assets)