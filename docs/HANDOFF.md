# 毫米波人体成像质量评价软件交接说明

更新时间：2026-04-27

## 项目概况

这是一个本地 Web 科研评测工具，用于评价毫米波人体成像结果图的成像质量。当前版本只处理已经成像后的图片，不处理原始雷达数据或成像重建流程。

当前技术栈：

- 后端：FastAPI + Pillow + NumPy + Pandas/OpenPyXL
- 前端：React + Vite + TypeScript
- 数据持久化：本地 `data/state.json`，上传图像在 `data/uploads/`，ROI mask 在 `data/masks/`

启动方式：

```powershell
python -m pip install -r backend/requirements.txt
npm install --prefix frontend
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`

## 当前已实现功能

- 支持文件导入和文件夹导入图片。
- 支持导入前文件列表预览、鼠标选择、键盘上下选择、勾选多张。
- 支持单张计算和勾选多张批量计算。
- 左侧栏目前只保留导入图片和权重设置。
- 主视觉区居中显示大尺寸图像和 ROI，便于人工观察成像质量。
- 样本排名缩小并放在右下角。
- 右侧显示人工分项评分、指标量化得分、图像特征和直方图。
- 支持 CSV、Excel、HTML 报告导出。

## 质量指标说明

后端真实读取图像像素并计算原始指标，位置在 `backend/app/processing.py`：

- `sharpness`：ROI 内 Laplacian 方差
- `local_contrast`：ROI 灰度标准差
- `snr`：ROI 均值与背景均值差 / 背景标准差
- `structure_continuity`：ROI mask 在包围盒内的填充比例
- `artifact_strength`：背景中异常高亮像素比例
- `body_area_ratio`：ROI 面积占全图比例
- `background_noise`：背景灰度标准差

前端显示的 `0-100` 量化得分不是固定行业标定分，而是后端在 `backend/app/scoring.py` 中对当前已计算样本集做 min-max 相对归一化：

- 越高越好：清晰度、局部对比、SNR、结构连续、人体占比、人工评分
- 越低越好：伪影强度、背景噪声

重要限制：如果当前只计算一张图，min=max，当前逻辑会把非零指标归一化为 100。因此单张图时原始值有意义，0-100 得分主要用于多图横向比较。

## 人工评分

人工评分已经从单个下拉框改为 5 个维度，每项 1-5 分：

- 人体轮廓清晰度
- 结构完整性
- 背景干扰控制
- 伪影可接受度
- 识别可用性

后端保存字段：

- `subjective_scores`
- `subjective_rating`
- `subjective_rating_complete`

`subjective_rating` 是已填写维度的均分。综合总分仍通过 `subjective_rating` 参与权重计算。

## 关键文件

后端：

- `backend/app/main.py`：FastAPI 路由，导入、评分、导出接口。
- `backend/app/storage.py`：本地状态读写、上传文件保存、人工评分保存。
- `backend/app/processing.py`：ROI 提取、客观指标、灰度/RGB 直方图计算。
- `backend/app/scoring.py`：权重归一化、指标方向、综合分和 0-100 指标得分。
- `backend/app/reports.py`：CSV、Excel、HTML 报告导出。

前端：

- `frontend/src/App.tsx`：主界面布局和主要交互。
- `frontend/src/styles.css`：页面布局和组件样式。
- `frontend/src/api.ts`：前后端接口封装。
- `frontend/src/importSelection.ts`：文件/文件夹导入列表、键盘选择、多选计算逻辑。
- `frontend/src/scoring.ts`：前端权重、指标名称、格式化。
- `frontend/src/histogram.ts`：SVG 直方图路径生成。
- `frontend/src/subjectiveRating.ts`：人工分项评分维度、均分、完成状态。
- `frontend/src/types.ts`：前端数据类型。

测试：

- `backend/tests/test_processing.py`
- `backend/tests/test_scoring.py`
- `backend/tests/test_storage.py`
- `frontend/src/*.test.ts`
- `frontend/src/App.visibility.test.tsx`

## 当前验证命令

```powershell
python -m pytest backend/tests
npm test --prefix frontend
npm run build --prefix frontend
```

最近一次验证状态：

- 后端测试：8 passed
- 前端测试：13 passed
- 前端构建：passed

## 已知问题和设计限制

- `0-100` 指标得分是当前样本集内的相对归一化，不是绝对物理评分。
- ROI 目前是阈值、形态学、最大连通域的粗分割，没有人工修正功能。
- 权重调整会重新计算当前已导入样本的综合分，但不会改变原始指标。
- 数据保存在本地 JSON，适合原型和小型科研实验，不适合多人并发或大规模数据库管理。
- 导入大量图片时，后端同步逐张计算，数据量很大时可能需要任务队列、进度条和取消机制。
- 目前没有去重策略，同一张图重复计算会形成多条记录。
- 当前人工评分是单人评分，没有评分者身份、多人一致性分析或评分历史。

## 建议后续任务

1. 将 0-100 得分从相对 min-max 改为可配置的固定阈值/经验区间评分。
2. 增加 ROI 手动修正功能，包括画框、涂抹、重算指标。
3. 增加导入进度条、批量计算取消、错误文件列表。
4. 增加样本去重和批量删除功能。
5. 增加多人评分、评分者 ID、评分一致性分析。
6. 增加图像对比模式，例如 A/B 双图同步查看。
7. 增加报告模板定制和实验配置保存。
8. 如果数据量继续增大，把 `data/state.json` 替换为 SQLite。

## 接手注意事项

- 不要把 `data/`、`frontend/dist/`、`node_modules/` 提交进版本控制。
- 修改指标计算前，应先补后端单测，尤其要覆盖指标方向和异常图像。
- 修改界面布局前，应补前端可见性测试，避免重要区域被条件渲染隐藏。
- 如果新增导出字段，需要同时更新 `backend/app/reports.py` 和前端类型。
- Windows PowerShell 终端有时会显示中文乱码，但浏览器和 UTF-8 文件内容应正常；不要因为终端显示乱码就随意改编码。
