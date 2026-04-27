# AI 工作总结：ROI 提取与前端交互改进

更新日期：2026-04-27

本文档总结本轮 AI 对 `D:\MMW_Imaging_Quality_Assessment‌` 项目完成的主要修改，便于后续 AI 或开发者快速了解上下文、改动原因、验证方式和剩余问题。

## 1. 背景问题

原始 ROI 提取逻辑位于 `backend/app/processing.py`，流程是：

1. 灰度归一化。
2. Otsu 阈值分割。
3. 面积异常时退回 `mean + 0.45 * std`。
4. 形态学闭运算、开运算。
5. 最大连通域。

在 `example_pic` 中，多张毫米波伪彩色人体图像出现以下问题：

- 正面图只分割出裤子、腿部或局部高反射区域。
- 头、肩、手臂、躯干暗部经常漏掉。
- 手臂、小腿、头部等人体弱反射区域与主体断开后会被最大连通域过滤掉。
- 更新算法后，如果后端服务没有重启，会继续用旧代码生成旧 mask。

## 2. ROI 算法改动

### 2.1 第一版改进：高置信种子 + 弱候选区域

修改文件：

- `backend/app/processing.py`
- `backend/tests/test_processing.py`

核心思路：

1. Otsu 结果不再直接作为最终 mask，而是作为高置信人体种子 `seed`。
2. 使用较低阈值生成弱候选区域 `weak`。
3. 仅保留与 `seed` 相交的候选区域。
4. 再做形态学后处理。

新增/修改的关键函数：

- `extract_body_mask`
- `_seeded_body_candidate`
- `_body_components_near_seed`
- `_add_nearby_detached_components`

第一版改善了 `1429_front.png`、`1602_front.png` 等图片只抓下半身的问题。

### 2.2 第二版改进：保留人体附近断开组件

用户反馈仍有部分图像无法完整识别人体，例如：

- `1063_front.png`
- `1093_front.png`
- `1615_front.png`
- `1000_front.png`

分析发现，弱候选区域中确实存在断开的手臂、头部、小腿组件，但它们没有与高置信种子连通，因此被丢弃。

进一步修改：

- 不再在最终阶段强制 `_largest_component(mask)`。
- 对弱候选组件做分类：
  - 与强种子相交的组件保留。
  - 不相交但位于人体主体附近、面积足够大、不贴图像边缘的组件也保留。
  - 贴边竖纹、过小噪声、过细长背景组件过滤掉。

新增测试覆盖：

- `test_extract_body_mask_recovers_full_front_body_when_reflection_is_uneven`
- `test_extract_body_mask_keeps_nearby_disconnected_body_parts`

已验证样本 bbox 改善：

- `1063_front`: 右侧边界从约 `x=284` 扩展到 `x=362`
- `1093_front`: 左侧边界从约 `x=126` 扩展到 `x=58`
- `1615_front`: 左侧边界从约 `x=145` 扩展到 `x=49`
- `1000_front`: 顶部边界从约 `y=269` 扩展到 `y=191`

诊断图生成位置：

- `data/diagnostics/detached_filtered_candidate_sheet.png`
- `data/diagnostics/updated_roi_contact_sheet.png`

## 3. 后端运行注意事项

曾发现用户重新导入后仍看到旧 mask。根因不是清空失败，而是正在运行的 uvicorn 后端进程没有加载最新代码。

检查方式：

```powershell
Get-CimInstance Win32_Process -Filter "name = 'python.exe'" | Select-Object ProcessId,CommandLine
```

正确启动方式应带 `--reload`：

```powershell
.\scripts\start-backend.ps1
```

如果后端没有加载新代码，可停掉旧进程后重启：

```powershell
Stop-Process -Id <旧后端进程ID> -Force
.\scripts\start-backend.ps1
```

清空现有数据的接口：

```powershell
Invoke-RestMethod -Method Delete -Uri http://127.0.0.1:8000/api/images
```

重要：算法更新不会自动重算 `data/masks` 中已经生成的旧 mask。需要清空数据后重新导入，或后续新增“重新计算 ROI”功能。

## 4. 前端功能改动

### 4.1 新增“清空数据”按钮

修改文件：

- `frontend/src/App.tsx`
- `frontend/src/App.visibility.test.tsx`

原来后端已有 `DELETE /api/images`，前端也已有 `resetImages()`，但界面上只有一个不明显的图标按钮。

改动：

- 右上角新增带文字的“清空数据”按钮。
- 点击后弹出确认框。
- 确认后清空已导入图片、ROI mask 和评分记录。

### 4.2 左侧“待计算文件”列表支持切换观察区

用户反馈右下角“样本排名”区域太小，用它切换“图像质量观察区”不方便。

修改文件：

- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.visibility.test.tsx`

实现方案：

- 左侧“待计算文件”列表现在兼具导航功能。
- 点击某个文件行：
  - 如果该文件已经计算过，则切换右侧“图像质量观察区”到对应图片。
  - 如果尚未计算，只改变当前待计算文件选择，不影响观察区。
- 复选框仍只控制是否参与批量计算，不触发观察区切换。
- 键盘上下键移动当前文件时，也会同步切换到对应已计算图片。
- 已计算文件行显示“已计算”。
- 当前正在观察的文件行增加绿色左侧标记。

关键新增逻辑：

- `normalizeDisplayPath`
- `basename`
- `findCalculatedImageForImportEntry`
- `selectCalculatedImportEntry`

匹配规则：

1. 优先用完整显示路径匹配，例如 `example_pic/1093_front.png`。
2. 如果完整路径不一致，则退回用 basename 匹配，例如 `1093_front.png`。

## 5. 验证命令

本轮最终验证过以下命令：

```powershell
python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
```

最近验证结果：

- 后端测试：`13 passed`
- 前端测试：`15 passed`
- 前端生产构建：成功

## 6. 当前已知限制

### 6.1 ROI 仍不是完美人体分割

当前算法仍是无监督传统图像处理，不是语义分割模型。它比原始 Otsu + 最大连通域更完整，但仍存在以下限制：

- 暗弱人体边界可能漏掉。
- 手臂与躯干之间可能仍有断裂。
- 背景竖纹和人体弱反射区域有时难以完全区分。
- 伪彩色图像直接转灰度会损失部分颜色通道信息，但测试中 RGB 最大通道方案改善有限，根因更多是弱反射组件断开。

### 6.2 已生成 mask 不会自动重算

`data/masks` 中的 PNG 是导入时生成的静态结果。修改 `processing.py` 后，旧 mask 不会自动变化。

建议后续新增：

- 单张“重新计算 ROI”按钮。
- 批量“重新计算全部 ROI”按钮。
- 后端接口如 `POST /api/images/recompute-masks`。

### 6.3 质量分数仍受 ROI 影响较大

ROI 改变会影响：

- 清晰度
- 局部对比度
- SNR
- 结构连续性
- 人体占比
- 背景噪声
- 综合质量分

因此后续比较算法版本时，应保留 ROI 算法版本号或参数记录。

## 7. 建议后续方向

### 短期

1. 增加“重新计算 ROI”前端按钮和后端接口。
2. 给 ROI 算法增加参数记录，例如 `roi_algorithm_version = seeded_components_v2`。
3. 在前端显示 ROI 诊断信息：mask 面积、bbox、是否含断开组件。
4. 允许用户手动排除明显错误 ROI 或标记失败样本。

### 中期

1. 标注 30-100 张代表性 mask。
2. 训练轻量 U-Net / DeepLab / SegFormer 分割模型。
3. 用当前传统算法生成粗 mask，模型或 SAM 做 refinement。
4. 建立 Dice、IoU、bbox 覆盖率、人体关键区域召回等评价指标。

### 关于 SAM

SAM/SAM2 可以尝试，但建议作为 refinement，而不是直接替代当前流程。原因：

- 当前图像是毫米波伪彩色图，和 SAM 自然图像训练域差异明显。
- 如果粗 ROI 或 prompt 不准，SAM 也可能失败。
- 更稳的路线是先用传统算法给出粗 bbox / 正负点，再用 SAM 做边界细化。

## 8. 关键文件清单

后端：

- `backend/app/processing.py`：ROI 提取和质量指标计算。
- `backend/app/storage.py`：导入图片、保存 mask、保存记录。
- `backend/app/main.py`：FastAPI 路由，包括清空数据接口。
- `backend/tests/test_processing.py`：ROI 和指标测试。

前端：

- `frontend/src/App.tsx`：主界面、导入、观察区切换、清空数据。
- `frontend/src/styles.css`：界面布局和文件行观察状态样式。
- `frontend/src/App.visibility.test.tsx`：前端可见行为测试。
- `frontend/src/api.ts`：前后端 API 封装。
- `frontend/src/importSelection.ts`：导入文件列表和键盘选择逻辑。

数据与诊断：

- `data/uploads/`：导入图片。
- `data/masks/`：导入时生成的 ROI mask。
- `data/state.json`：本地记录状态。
- `data/diagnostics/`：本轮调试生成的 ROI 对比图。

