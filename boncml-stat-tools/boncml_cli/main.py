#!/usr/bin/env python3
"""BONCML CLI 统一命令行入口"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from boncml import get_catalog, _run_algo_directly
    from boncml import _get_python_path, _get_runtime_root
    from boncml import _normalize_args_for_algo
except ImportError as e:
    print(f"错误：无法导入 BONCML 模块: {e}")
    print("请确保已正确安装 boncml-stat-tools")
    sys.exit(1)

from boncml_cli.algo_specs import SPECS


def detect_python_env() -> Optional[str]:
    """检测可用的 Python 环境"""
    common_envs = ["spss-fortran", "boncml", "stats", "data-science"]
    for env_name in common_envs:
        conda_prefix = os.environ.get("CONDA_PREFIX", "")
        if conda_prefix and env_name in conda_prefix:
            return conda_prefix
    try:
        import numpy
        import pandas
        return sys.prefix
    except ImportError:
        return None


def create_parser() -> argparse.ArgumentParser:
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        prog="boncml",
        description="BONCML 统计分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  boncml list                          # 列出所有算法
  boncml version                       # 显示版本信息
  boncml regress --data data.csv --dependent y --independents x1 x2
  boncml acf --data data.csv --series sales --acf --maxlag 16
  boncml inspect data.csv              # 查看数据集概览
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list 命令
    subparsers.add_parser("list", help="列出所有可用的算法")

    # version 命令
    subparsers.add_parser("version", help="显示版本信息")

    # run 命令 (legacy interactive mode)
    run_parser = subparsers.add_parser("run", help="执行统计分析算法（交互模式）")
    run_parser.add_argument("algorithm", help="算法名称 (如: regress, ttest, oneway)")
    run_parser.add_argument("--data", required=True, help="数据文件路径 (CSV/Excel)")
    run_parser.add_argument("--output", "-o", help="输出结果文件路径 (JSON格式)")

    # inspect 命令
    inspect_parser = subparsers.add_parser("inspect", help="查看数据集概览")
    inspect_parser.add_argument("data_path", help="数据文件路径")

    # ---- 动态注册所有算法子命令 ----
    for algo_name, spec in SPECS.items():
        epilog = spec.get("examples")
        parser_kwargs = {"help": spec["help"]}
        if epilog:
            parser_kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
            parser_kwargs["epilog"] = epilog
        p = subparsers.add_parser(algo_name, **parser_kwargs)
        p.add_argument("--data", required=True, help="数据文件路径 (CSV/Excel/.sav)")
        for flags, kwargs in spec["args"]:
            p.add_argument(*flags, **kwargs)
        p.add_argument("--output", choices=["table", "json"], default="table", help="输出格式")
        p.add_argument("--save", help="保存结果到文件")

    return parser


def cmd_list(args: argparse.Namespace) -> int:
    """列出所有算法"""
    print("可用算法列表:")
    print("=" * 60)
    catalog = get_catalog()
    count = 0
    for entry in catalog.values():
        if entry.algo_name not in SPECS:
            continue
        count += 1
        desc = entry.schema.get("description", "No description")
        if len(desc) > 50:
            desc = desc[:47] + "..."
        print(f"  {entry.tool_name:<20} {entry.algo_name:<15} {desc}")
    print(f"\n共 {count} 个算法")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """显示版本信息"""
    from boncml_cli import __version__
    print(f"boncml-stat-tools v{__version__}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """运行算法（交互模式）"""
    if not os.path.exists(args.data):
        print(f"错误：数据文件不存在: {args.data}")
        return 1

    catalog = get_catalog()
    entry = catalog.get(args.algorithm)
    if not entry:
        for e in catalog.values():
            if e.tool_name == args.algorithm:
                entry = e
                break
        if not entry:
            print(f"错误：未知算法 '{args.algorithm}'")
            print("使用 'boncml list' 查看可用算法")
            return 1

    params = {"data_path": os.path.abspath(args.data)}

    schema = entry.schema
    if "parameters" in schema and "properties" in schema["parameters"]:
        for param_name, param_def in schema["parameters"]["properties"].items():
            if param_name != "data_path" and param_name in schema["parameters"].get("required", []):
                print(f"需要参数: {param_name}")
                print(f"  描述: {param_def.get('description', '')}")
                if param_def.get("type") == "array":
                    print(f"  类型: 数组 (示例: '[\"col1\", \"col2\"]')")
                else:
                    print(f"  类型: 字符串")
                value = input(f"输入 {param_name}: ")
                try:
                    params[param_name] = json.loads(value)
                except json.JSONDecodeError:
                    params[param_name] = value

    python_path = _get_python_path()
    if python_path:
        os.environ["BONCML_PYTHON_PATH"] = python_path

    try:
        runtime_root, _ = _get_runtime_root()
        if not runtime_root:
            print("错误：未找到算法运行时资源（vendored 目录缺失）")
            return 1
        normalized_params, notices = _normalize_args_for_algo(entry.algo_name, params)
        result_dict = _run_algo_directly(
            entry.algo_name, normalized_params,
            runtime_root,
        )
        formatted_result = entry.format_fn(result_dict)
        if args.output:
            print(f"结果已保存到: {args.output}")
        else:
            print("\n分析结果:")
            print("-" * 50)
            print(formatted_result)
        return 0
    except Exception as e:
        print(f"执行错误: {e}")
        return 1


def cmd_algo(args: argparse.Namespace) -> int:
    """通用算法执行：通过 algo_specs 映射 CLI 参数到 API 参数"""
    algo_name = args.command
    spec = SPECS.get(algo_name)
    if not spec:
        print(f"错误：未注册算法 '{algo_name}'")
        return 1

    if not os.path.exists(args.data):
        print(f"错误：数据文件不存在: {args.data}")
        return 1

    # 构建 API 参数
    params = {"data_path": os.path.abspath(args.data)}
    params = spec["build"](args, params)

    # 获取算法入口
    catalog = get_catalog()
    entry = catalog.get(algo_name)
    if not entry:
        print(f"错误：未找到 {algo_name} 算法模块")
        return 1

    python_path = _get_python_path()
    if python_path:
        os.environ["BONCML_PYTHON_PATH"] = python_path

    try:
        runtime_root, _ = _get_runtime_root()
        if not runtime_root:
            print("错误：未找到算法运行时资源（vendored 目录缺失）")
            return 1
        normalized_params, notices = _normalize_args_for_algo(algo_name, params)
        result_dict = _run_algo_directly(
            algo_name, normalized_params,
            runtime_root,
        )

        if getattr(args, "output", "table") == "json":
            print(json.dumps(result_dict, ensure_ascii=False, indent=2, default=str))
        else:
            formatted_result = entry.format_fn(result_dict)
            print(formatted_result)

        save_path = getattr(args, "save", None)
        if save_path:
            with open(save_path, "w") as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str)
            print(f"结果已保存到: {save_path}")

        return 0
    except Exception as e:
        print(f"执行错误: {e}")
        return 1


def cmd_inspect(args: argparse.Namespace) -> int:
    """查看数据集概览"""
    if not os.path.exists(args.data_path):
        print(f"错误：数据文件不存在: {args.data_path}")
        return 1
    try:
        import pandas as pd
        df = pd.read_csv(args.data_path, nrows=1000)
        print("数据集概览:")
        print("=" * 60)
        print(f"文件路径: {os.path.abspath(args.data_path)}")
        print(f"行数: {len(df):,}")
        print(f"列数: {len(df.columns)}")
        print()
        print("列名 (前10列):")
        for col in df.columns[:10]:
            print(f"  {col}")
        if len(df.columns) > 10:
            print(f"  ... 还有 {len(df.columns) - 10} 列")
        print()
        print("数据类型:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].count()
            null_pct = (1 - non_null / len(df)) * 100
            print(f"  {col}: {dtype} (非空: {non_null}, 缺失: {null_pct:.1f}%)")
        return 0
    except Exception as e:
        print(f"读取数据错误: {e}")
        return 1


def main() -> int:
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 检查环境
    if args.command in ["run"] or args.command in SPECS:
        python_env = detect_python_env()
        if not python_env:
            print("警告：未检测到合适的 Python 环境")
            print("请确保已安装 numpy, pandas 以及 Fortran 编译的 .so 文件")
            print("推荐使用 conda 环境: conda create -n spss-fortran python=3.11 numpy pandas")
            return 1

    try:
        if args.command == "list":
            return cmd_list(args)
        elif args.command == "version":
            return cmd_version(args)
        elif args.command == "run":
            return cmd_run(args)
        elif args.command == "inspect":
            return cmd_inspect(args)
        elif args.command in SPECS:
            return cmd_algo(args)
        else:
            print(f"未知命令: {args.command}")
            return 1
    except KeyboardInterrupt:
        print("\n操作已取消")
        return 1


if __name__ == "__main__":
    sys.exit(main())
