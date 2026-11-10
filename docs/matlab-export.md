# 按需导出 MATLAB 文件

在算例目录打开 `input.json`，点击 GitHub 的 **Download raw file** 可下载源输入。需要 MATLAB 格式时，下载同一份 JSON，并在本地按需转换。仓库保存 JSON 和转换代码，生成的 MAT 文件由使用者保存到本机。

## 用按钮转换

需要 Python 3.10 或更新版本、SciPy 及 Python 自带的 Tk 图形组件。Windows 安装 Python 时可勾选 Tcl/Tk 组件。安装 SciPy 后，从仓库根目录运行：

```text
python -m pip install scipy
python scripts/export_orlib_mat.py
```

点「选择 JSON 并另存 MAT」，选中算例文件，然后选择 MAT 文件的保存位置。后续转换可直接运行第二条命令。转换过程在本地执行，输出文件需使用新文件名，且应保存到支持硬链接的本地文件系统（如 NTFS）。

也可以直接用命令行转换：

```text
python scripts/export_orlib_mat.py cases/orlib_20_0_1_w/input.json orlib_20.mat
```

## 在 MATLAB 读取

```matlab
data = load('orlib_20.mat', 'uc');
uc = data.uc;
demand = uc.demand_MW;    % 24×1，单位 MW
reserve = uc.reserve_MW;  % 24×1，单位 MW
generators = uc.generators;
```

目前支持本库 OR-LIB 10、20、50 台机组的 UC.jl JSON 布局，即单节点、24 小时、单项旋转备用。支持 `.json` 和 `.json.gz`。导出保留机组顺序、原机组编号、带符号的初始状态、全部成本折点、启动费用档位和备用。原始 JSON 文本在 `uc.source_json`，所读源文件的 SHA-256 在 `uc.sources`。MAT 为算例输入，具体模型规则见对应算例说明。IEEE24 和 RTS24 的源数据布局另有说明。
