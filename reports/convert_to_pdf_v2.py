# -*- coding: utf-8 -*-
"""
HTML to PDF Converter using Playwright
使用Playwright将HTML报告转换为PDF格式
"""

import os
from pathlib import Path
import asyncio

async def convert_html_to_pdf():
    """使用playwright将HTML文件转换为PDF"""
    try:
        from playwright.async_api import async_playwright

        # 当前目录
        current_dir = Path(__file__).parent

        # 要转换的HTML文件
        html_files = [
            'openalex_citation_report.html',
            'openalex_authors_report.html'
        ]

        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch()
            page = await browser.new_page()

            for html_file in html_files:
                html_path = current_dir / html_file
                pdf_file = html_file.replace('.html', '.pdf')
                pdf_path = current_dir / pdf_file

                if not html_path.exists():
                    print(f"错误: 找不到文件 {html_path}")
                    continue

                print(f"正在转换: {html_file} -> {pdf_file}")

                try:
                    # 打开HTML文件
                    await page.goto(f'file:///{html_path.as_posix()}')

                    # 转换为PDF
                    await page.pdf(
                        path=str(pdf_path),
                        format='A4',
                        print_background=True,
                        margin={
                            'top': '10mm',
                            'right': '10mm',
                            'bottom': '10mm',
                            'left': '10mm'
                        }
                    )

                    print(f"[成功] 生成: {pdf_file}")
                    print(f"  文件大小: {pdf_path.stat().st_size / 1024:.2f} KB")
                except Exception as e:
                    print(f"[失败] 转换 {html_file}: {str(e)}")

            await browser.close()

        print("\n转换完成!")

    except ImportError:
        print("错误: 未安装 playwright 库")
        print("正在尝试安装...")
        import subprocess
        subprocess.run(['pip', 'install', 'playwright'], check=True)
        subprocess.run(['playwright', 'install', 'chromium'], check=True)
        print("安装完成，请重新运行此脚本")

if __name__ == '__main__':
    asyncio.run(convert_html_to_pdf())
