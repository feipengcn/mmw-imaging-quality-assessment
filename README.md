# 毫米波人体成像质量评价软件 v1

本项目是一个本地 Web 科研评测工具，用于批量导入毫米波人体成像结果图，自动提取人体 ROI，计算无参考质量指标，记录人工评分，并导出指标表和 HTML 报告。

## 功能

- 支持文件导入或文件夹导入 PNG、JPG、TIFF、BMP 图像。
- 文件夹导入后显示完整待计算文件列表，可用鼠标或方向键选择预览图片。
- 支持单张计算和勾选多张批量计算。
- 按实验组、算法、参数、批次管理样本。
- 自动人体区域粗分割并保存 ROI mask。
- 计算清晰度、局部对比、信噪比、结构连续性、伪影强度、人体占比、背景噪声。
- 展示每个指标的原始值、0-100 量化得分和当前权重。
- 展示灰度直方图和 RGB 直方图，用于直观查看图像灰度分布与通道特征。
- 支持权重滑杆重新计算综合质量分。
- 支持 1-5 分人工评分和备注。
- 人工评分包含人体轮廓清晰度、结构完整性、背景干扰控制、伪影可接受度、识别可用性 5 个维度，并自动计算人工均分。
- 导出 CSV、Excel、HTML 报告。

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

浏览器打开 `http://127.0.0.1:5173`。

## 验证

```powershell
python -m pytest backend/tests
npm test --prefix frontend
npm run build --prefix frontend
```

## 数据位置

运行时数据保存在 `data/`，包括上传图像、ROI mask 和 `state.json`。该目录默认不纳入版本控制。
