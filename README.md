# 毫米波人体成像质量评价软件 v1

本项目是一个本地 Web 科研评测工具，用于批量导入毫米波人体成像结果图，自动提取人体 AOI，计算无参考质量指标，并导出结构化结果。

## 当前状态

当前主线版本已经完成以下能力：

- 左侧统一样本列表，合并了导入区和排序浏览区。
- 支持文件导入和文件夹导入 PNG、JPG、TIFF、BMP 图像。
- 支持对勾选样本批量计算、全选、清空、删除。
- 支持批量计算进度显示，包括已完成数量和当前处理文件名。
- 主视图区采用竖版主图，支持原图、AOI、伪影溢出带、饱和条纹区切换。
- 右侧展示灰度/R/G/B 直方图、雷达图和原始物理指标。
- 权重控制位于右上角设置面板。
- 支持导出 CSV、Excel、HTML 报告。

## 架构

- `backend/`: FastAPI 后端，负责导入、AOI 提取、指标计算、评分和导出。
- `frontend/`: React + Vite 前端，负责样本操作、图像查看、进度显示和指标展示。
- `data/`: 运行时数据目录，保存上传图像、mask、overlay 和 `state.json`。
- `example_pic/`: 视角分类参考图。
- `docs/`: 设计、交接、计划和文档索引。

## 启动

先安装依赖：

```powershell
python -m pip install -r backend/requirements.txt
npm install --prefix frontend
```

启动后端：

```powershell
.\scripts\start-backend.ps1
```

启动前端：

```powershell
.\scripts\start-frontend.ps1
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`

## 验证

```powershell
python -m pytest
npm test --prefix frontend
npm run build --prefix frontend
```

## 关键接口

- `GET /api/images`: 获取当前样本和权重。
- `POST /api/import`: 普通批量导入接口。
- `POST /api/import/progress`: 流式批量导入接口，返回换行分隔 JSON 进度事件。
- `POST /api/images/score`: 按当前权重重新评分。
- `DELETE /api/images/:id`: 删除单个样本。
- `GET /api/export/csv|excel`: 导出表格。
- `GET /api/report/html`: 导出 HTML 报告。

## 已知输入约束

- 外圈强白边会干扰 AOI 提取，进而影响 CNR 等背景相关指标。
- 当前建议是在导入前先去掉明显白边，而不是依赖程序自动修正。

## 文档

- 项目总览：`README.md`
- 当前工程与运行约束：`AGENT.md`
- 视觉与布局基线：`DESIGN.md`
- 文档索引：`docs/README.md`
