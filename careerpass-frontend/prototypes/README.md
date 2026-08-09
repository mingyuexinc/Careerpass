# Careerpass 前端原型开发包

本目录用于保存 Careerpass 正式前端开发前的 HTML 交互原型、验证 Mock 数据和视觉参考资源。

## 目录说明

- `html-reference/`：可直接运行的 HTML 原型页面。
- `reference-data/`：原型参考使用的固定 Mock 数据。
- `resources/`：页面视觉参考图片和功能模板图片。

## 运行方式

原型为单页面静态 HTML，无需安装依赖或执行构建命令。

可以直接用浏览器打开：

```text
html-reference/index.html
```

也可以在 `prototypes/` 目录下启动一个本地静态文件服务器：

```powershell
python -m http.server 8000
```

然后访问：<http://localhost:8000/html-reference/index.html>

## 注意事项

- 本目录仅用于原型参考和正式前端开发参考，不属于正式前端源码。
- 原型中的岗位、投递、消息和状态数据为本地参考数据，不代表真实后端数据。
- 正式前端源码位于项目根目录的 `src/`，正式前端文档位于 `docs/`。
