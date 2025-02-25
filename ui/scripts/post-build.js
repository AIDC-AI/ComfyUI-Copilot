import fs from 'fs';
import path from 'path';
import glob from 'glob';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// 获取 __dirname 的等效值
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 在 dist/copilot_web 目录下查找包含 __vite__mapDeps 的 JS 文件
const distDir = path.resolve(__dirname, '../../dist/copilot_web');
const files = glob.sync(`${distDir}/**/App-*.js`);

// 处理依赖映射
files.forEach(file => {
    console.log('start modify', file)
    let content = fs.readFileSync(file, 'utf-8');

    if (content.includes('__vite__mapDeps')) {
        // 提取新格式的依赖数组，使用非贪婪匹配
        const depsMatch = content.match(/const __vite__mapDeps=\(.*?m\.f=\[(.*?)\]/);
        if (depsMatch && depsMatch[1]) {
            const originalDeps = depsMatch[1];
            
            // 如果文件中还没有路径转换逻辑，则添加
            if (!content.includes('window.comfyAPI?.api?.api?.api_base')) {
                content = content.replace(
                    /const __vite__mapDeps=.*?\)=>i\.map\(i=>d\[i\]\);/,
                    `const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=[${originalDeps}].map(path => {
                        const apiBase = window.comfyAPI?.api?.api?.api_base;
                        const prefix = apiBase ? \`\${apiBase.substring(1)}/\` : '';
                        return \`\${prefix}\${path}\`;
                    }))))=>i.map(i=>d[i]);`
                );
            } else {
                // 如果已经有路径转换逻辑，只替换依赖数组部分
                content = content.replace(
                    /const __vite__mapDeps=\(.*?\)=>i\.map\(i=>d\[i\]\);/,
                    `const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=[${originalDeps}])))=>i.map(i=>d[i]);`
                );
            }

            fs.writeFileSync(file, content, 'utf-8');
            console.log(`Modified ${path.basename(file)}`);
        } else {
            console.log(`No deps pattern found in ${path.basename(file)}`);
        }
    } else {
        console.log(`No __vite__mapDeps found in ${path.basename(file)}`);
    }
});

// 处理 logo 图片路径
const allJsFiles = glob.sync(`${distDir}/**/*.js`);
allJsFiles.forEach(file => {
    let content = fs.readFileSync(file, 'utf-8');
    
    // 查找包含 logo 图片路径的内容
    if (content.includes('/copilot_web/assets/logo-')) {
        console.log('Found logo reference in', file);
        
        // 替换 logo 路径的引用方式
        content = content.replace(
            /(?<=[,{]\s*E=)"\/copilot_web\/assets\/logo-[^"]+"/g,
            `(window.comfyAPI?.api?.api?.api_base ? \`\${window.comfyAPI.api.api.api_base.substring(1)}/copilot_web/assets/logo-BTZhX0BN.png\` : "/copilot_web/assets/logo-BTZhX0BN.png")`
        );
        
        fs.writeFileSync(file, content, 'utf-8');
        console.log(`Modified logo path in ${path.basename(file)}`);
    }
}); 