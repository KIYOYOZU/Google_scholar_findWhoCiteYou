# -*- coding: utf-8 -*-
"""
HTML to PDF Converter
将HTML报告转换为PDF格式
"""

import os
from pathlib import Path

def convert_html_to_pdf():
    """使用weasyprint将HTML文件转换为PDF"""
    try:
        from weasyprint import HTML

        # 当前目录
        current_dir = Path(__file__).parent

        # 要转换的HTML文件
        html_files = [
            'openalex_citation_report.html',
            'openalex_authors_report.html'
        ]

        for html_file in html_files:
            html_path = current_dir / html_file
            pdf_file = html_file.replace('.html', '.pdf')
            pdf_path = current_dir / pdf_file

            if not html_path.exists():
                print(f"错误: 找不到文件 {html_path}")
                continue

            print(f"正在转换: {html_file} -> {pdf_file}")

            try:
                # 转换HTML到PDF
                HTML(filename=str(html_path)).write_pdf(str(pdf_path))
                print(f"✓ 成功生成: {pdf_file}")
                print(f"  文件大小: {pdf_path.stat().st_size / 1024:.2f} KB")
            except Exception as e:
                print(f"✗ 转换失败 {html_file}: {str(e)}")

        print("\n转换完成!")

    except ImportError:
        print("错误: 未安装 weasyprint 库")
        print("正在尝试安装...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'weasyprint'])
        print("安装完成，请重新运行此脚本")

if __name__ == '__main__':
    convert_html_to_pdf()
