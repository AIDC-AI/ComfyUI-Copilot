function getImportPath(filename) {
            return `./${filename}`;
        }
            const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["copilot_web/workflowChat-DQCCmkLv.js","copilot_web/vendor-markdown-CBmlBP6m.js","copilot_web/vendor-react-Dixhfmvb.js","copilot_web/message-components-C62Ox0cV.js","copilot_web/input.js","copilot_web/assets/input-DE7zKDA4.css","copilot_web/fonts.css"].map(path => {
                        const apiBase = window.comfyAPI?.api?.api?.api_base;
                        if (apiBase) {
                            // 有 API base 时，使用完整路径
                            return `${apiBase.substring(1)}/${path}`;
                        } else {        
                            // 没有 API base 时，使用相对路径
                            return `./${path}`;
                        }
                    }))))=>i.map(i=>d[i]);
import{_ as a}from"./input.js";import{j as e}from"./vendor-markdown-CBmlBP6m.js";import{r as t,R as i}from"./vendor-react-Dixhfmvb.js";import{C as n}from"./message-components-C62Ox0cV.js";/* empty css     */const o={EXPLAIN_NODE:"copilot:explain-node"},d=i.lazy(()=>a(()=>import(getImportPath("workflowChat-DQCCmkLv.js")),__vite__mapDeps([0,1,2,3,4,5,6])).then(r=>({default:r.default})));function p(){const[r,s]=t.useState(!1);return t.useEffect(()=>{const l=()=>{s(!0)};return window.addEventListener(o.EXPLAIN_NODE,l),()=>window.removeEventListener(o.EXPLAIN_NODE,l)},[]),e.jsx(n,{children:e.jsx("div",{className:"h-full w-full flex flex-col",children:e.jsx(t.Suspense,{fallback:e.jsx("div",{className:"h-full w-full flex items-center justify-center",children:"Loading..."}),children:e.jsx(d,{visible:!0,triggerUsage:r,onUsageTriggered:()=>s(!1)})})})})}export{p as default};
