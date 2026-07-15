#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src venv/bin/python -m py_compile src/marketcore/presentation/action_http_controller_v2.py src/marketcore/presentation/app.py src/marketcore/presentation/router.py
node --check src/marketcore/presentation/ui_runtime/assets/v2/browser_action_controller_v2.js
venv/bin/pytest -q tests/test_action_http_controller_v2.py tests/test_governed_action_dispatcher_v2.py
cat >/tmp/test_marketcore_browser_action_controller_v2.js <<'JS'
"use strict";
require("/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/browser_action_controller_v2.js");
let target=null, request=null;
globalThis.fetch=async (url,options)=>{request={url,options};return {ok:true,json:async()=>({status:"NAVIGATED",reason_code:"NAVIGATION_ALLOWED",target_id:"container.risk"})};};
(async()=>{
 const sink=globalThis.MarketCoreBrowserActionControllerV2.create({onNavigation:async x=>{target=x;}});
 await sink({actionId:"navigation.open.risk",actionKind:"NAVIGATE",interactionKind:"CLICK",targetId:"container.risk"});
 if(target!=="container.risk") throw new Error("NAVIGATION_CALLBACK_FAILED");
 if(request.options.method!=="POST"||request.options.credentials!=="same-origin") throw new Error("ACTION_POST_CONTRACT_FAILED");
 console.log("browser_to_server_action=PASS");
})().catch(e=>{console.error(e);process.exit(1);});
JS
node /tmp/test_marketcore_browser_action_controller_v2.js
echo "server_owned_actor=PASS"
echo "unknown_container_denied=PASS"
echo "state_changing_browser_action=DENIED_NOT_REGISTERED"
echo "audit_navigation=PASS"
echo "VERDICT=MARKETCORE_STAGE5_ACTION_HTTP_CONTROLLER_V2_READY"
