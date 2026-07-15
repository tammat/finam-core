#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
driver=src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js
bootstrap=src/marketcore/presentation/ui_runtime/assets/v2/browser_bootstrap_v2.js
node --check "$driver"
node --check "$bootstrap"
cat >/tmp/test_marketcore_browser_action_intents_v2.js <<'JS'
"use strict";
require("/opt/finam-core/src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js");
class Element {
  constructor(tag) { this.tagName=tag; this.attributes={}; this.children=[]; this.listeners={}; }
  setAttribute(k,v) { this.attributes[k]=String(v); }
  appendChild(x) { this.children.push(x); }
  replaceChildren() { this.children=[]; }
  addEventListener(k,fn) { (this.listeners[k] ||= []).push(fn); }
  emit(k,event={key:"",preventDefault(){}}) { for (const fn of this.listeners[k]||[]) fn(event); }
}
class Document { createElement(tag) { return new Element(tag); } }
const mount=new Element("mount"), events=[];
const driver=new globalThis.MarketCoreBrowserPlatformDriverV2.Driver({documentObject:new Document(),mountElement:mount,actionSink:x=>events.push(x)});
const root={type:"workspace",node_id:"root",children:[]};
const action={type:"card",node_id:"research",content:null,state:null,children:[],action:{action_id:"navigation.open.research",action_kind:"NAVIGATE",target_id:"container.research",enabled:true,requires_approval:false,reversible:false}};
driver.beginDocument(); driver.renderNode(root,{depth:0,displayValue:null}); driver.renderNode(action,{depth:1,displayValue:null}); driver.endDocument();
const element=mount.children[0].children[0];
element.emit("click"); element.emit("dblclick"); element.emit("keydown",{key:"Enter",preventDefault(){}});
if (events.map(x=>x.interactionKind).join(",") !== "CLICK,DOUBLE_CLICK,CLICK") throw new Error("INTERACTION_MAPPING_FAILED");
if (!events.every(x=>x.actionId==="navigation.open.research" && x.targetId==="container.research")) throw new Error("ACTION_ID_MAPPING_FAILED");
if (element.attributes.role !== "link" || element.attributes.tabindex !== "0") throw new Error("ACTION_ACCESSIBILITY_FAILED");
console.log("browser_action_events=3");
JS
node /tmp/test_marketcore_browser_action_intents_v2.js
if grep -nE 'fetch\(|location\.|XMLHttpRequest|WebSocket' "$driver"; then
  echo BROWSER_DRIVER_DIRECT_EXECUTION_FOUND
  exit 1
fi
echo "click_action_intent=PASS"
echo "double_click_action_intent=PASS"
echo "keyboard_action_intent=PASS"
echo "direct_execution_in_driver=0"
echo "VERDICT=MARKETCORE_STAGE5_BROWSER_ACTION_INTENTS_V2_READY"
