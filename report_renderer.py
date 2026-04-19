"""
报告渲染模块 - 将 Markdown 报告转换为精美的 HTML 页面并保存
设计风格：学术精炼 + 暗色主题 + 动感排版
"""

import os
import re
from datetime import datetime


def _md_to_html(md: str) -> str:
    """将 Markdown 文本转换为 HTML（轻量级，无外部依赖）"""
    lines = md.split('\n')
    html_lines = []
    in_table = False
    in_code = False
    in_list = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # 代码块
        if line.strip().startswith('```'):
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False
            else:
                lang = line.strip()[3:].strip()
                html_lines.append(f'<pre><code class="lang-{lang}">')
                in_code = True
            i += 1
            continue

        if in_code:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            i += 1
            continue

        # 关闭未结束的列表
        if in_list and not line.strip().startswith('-') and not line.strip().startswith('*'):
            html_lines.append('</ul>')
            in_list = False

        # 表格
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                html_lines.append('<table>')
                in_table = True
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                html_lines.append('<thead><tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr></thead><tbody>')
                i += 2  # 跳过分隔行
                continue
            else:
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                html_lines.append('<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in cells) + '</tr>')
                i += 1
                continue
        else:
            if in_table:
                html_lines.append('</tbody></table>')
                in_table = False

        # 标题
        if line.startswith('#### '):
            html_lines.append(f'<h4 class="anim-fade">{_inline(line[5:])}</h4>')
        elif line.startswith('### '):
            html_lines.append(f'<h3 class="anim-fade">{_inline(line[4:])}</h3>')
        elif line.startswith('## '):
            html_lines.append(f'<h2 class="anim-up">{_inline(line[3:])}</h2>')
        elif line.startswith('# '):
            html_lines.append(f'<h1 class="anim-up">{_inline(line[2:])}</h1>')
        # 水平线
        elif line.strip() in ('---', '***', '___'):
            html_lines.append('<hr/>')
        # 列表
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{_inline(line.strip()[2:])}</li>')
        # 有序列表
        elif re.match(r'^\d+\. ', line.strip()):
            if not in_list:
                html_lines.append('<ol>')
                in_list = True
            cleaned = re.sub(r'^\d+\. ', '', line.strip())
            html_lines.append(f'<li>{_inline(cleaned)}</li>')
        # 空行
        elif line.strip() == '':
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br/>')
        # 普通段落
        else:
            html_lines.append(f'<p>{_inline(line)}</p>')

        i += 1

    if in_list:
        html_lines.append('</ul>')
    if in_table:
        html_lines.append('</tbody></table>')

    return '\n'.join(html_lines)


def _inline(text: str) -> str:
    """处理行内 Markdown（粗体、斜体、行内代码、链接）"""
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text


def _build_html(title: str, body_html: str, generated_at: str) -> str:
    """拼装完整 HTML 页面"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Noto+Serif+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --bg:        #0d1117;
      --surface:   #161b22;
      --border:    #30363d;
      --text:      #e6edf3;
      --muted:     #8b949e;
      --accent:    #d4a853;
      --accent2:   #58a6ff;
      --danger:    #f85149;
      --radius:    12px;
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Noto Serif SC', serif;
      font-size: 16px;
      line-height: 1.85;
      min-height: 100vh;
    }}

    /* ── 顶部封面 ── */
    .cover {{
      position: relative;
      padding: 80px 40px 60px;
      text-align: center;
      overflow: hidden;
      border-bottom: 1px solid var(--border);
    }}
    .cover::before {{
      content: '';
      position: absolute;
      inset: 0;
      background:
        radial-gradient(ellipse 80% 60% at 50% -10%, rgba(212,168,83,.18) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(88,166,255,.10) 0%, transparent 70%);
      pointer-events: none;
    }}
    .cover-tag {{
      display: inline-block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--accent);
      border: 1px solid rgba(212,168,83,.35);
      padding: 4px 14px;
      border-radius: 100px;
      margin-bottom: 28px;
    }}
    .cover h1 {{
      font-family: 'Playfair Display', serif;
      font-size: clamp(26px, 4vw, 48px);
      font-weight: 900;
      line-height: 1.2;
      letter-spacing: -.02em;
      color: #fff;
      margin-bottom: 20px;
      max-width: 860px;
      margin-inline: auto;
    }}
    .cover-meta {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: .06em;
    }}

    /* ── 主体内容 ── */
    .container {{
      max-width: 860px;
      margin: 0 auto;
      padding: 48px 24px 96px;
    }}

    /* ── 标题样式 ── */
    h1 {{ display: none; }}   /* 封面已有 h1，正文里隐藏 */
    h2 {{
      font-family: 'Playfair Display', serif;
      font-size: 26px;
      font-weight: 700;
      color: #fff;
      margin: 56px 0 18px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
      position: relative;
    }}
    h2::before {{
      content: '';
      position: absolute;
      left: 0; bottom: -1px;
      width: 60px; height: 2px;
      background: var(--accent);
      border-radius: 2px;
    }}
    h3 {{
      font-family: 'Playfair Display', serif;
      font-size: 19px;
      font-weight: 600;
      color: var(--accent);
      margin: 32px 0 10px;
    }}
    h4 {{
      font-size: 15px;
      font-weight: 700;
      color: var(--text);
      margin: 20px 0 6px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}

    /* ── 正文元素 ── */
    p {{ margin: 0 0 14px; color: #cdd9e5; }}
    strong {{ color: #fff; font-weight: 700; }}
    em {{ color: var(--accent); font-style: normal; }}
    a {{ color: var(--accent2); text-decoration: none; border-bottom: 1px solid rgba(88,166,255,.3); }}
    a:hover {{ border-color: var(--accent2); }}
    code {{
      font-family: 'JetBrains Mono', monospace;
      font-size: .85em;
      background: rgba(110,118,129,.1);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 1px 6px;
      color: #ff7b72;
    }}
    pre {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      overflow-x: auto;
      margin: 20px 0;
    }}
    pre code {{
      background: none; border: none; padding: 0; color: #e6edf3; font-size: 13px;
    }}
    hr {{ border: none; border-top: 1px solid var(--border); margin: 40px 0; }}
    br {{ display: block; margin: 4px 0; }}

    /* ── 列表 ── */
    ul, ol {{
      margin: 8px 0 18px 0;
      padding-left: 0;
      list-style: none;
    }}
    ul li, ol li {{
      position: relative;
      padding: 6px 0 6px 24px;
      color: #cdd9e5;
      border-bottom: 1px solid rgba(48,54,61,.6);
    }}
    ul li:last-child, ol li:last-child {{ border-bottom: none; }}
    ul li::before {{
      content: '▸';
      position: absolute; left: 0;
      color: var(--accent);
      font-size: 12px;
      top: 9px;
    }}
    ol {{ counter-reset: li; }}
    ol li::before {{
      counter-increment: li;
      content: counter(li) '.';
      position: absolute; left: 0;
      color: var(--accent);
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      top: 8px;
    }}

    /* ── 表格 ── */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      font-size: 14px;
    }}
    th {{
      background: var(--surface);
      color: var(--accent);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
      padding: 10px 14px;
      border: 1px solid var(--border);
      text-align: left;
    }}
    td {{
      padding: 10px 14px;
      border: 1px solid var(--border);
      color: #cdd9e5;
      vertical-align: top;
    }}
    tr:nth-child(even) td {{ background: rgba(22,27,34,.5); }}

    /* ── 页脚 ── */
    .footer {{
      text-align: center;
      padding: 32px 0;
      border-top: 1px solid var(--border);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--muted);
      letter-spacing: .08em;
    }}

    /* ── 动画 ── */
    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(24px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to   {{ opacity: 1; }}
    }}
    .anim-up  {{ animation: fadeUp .6s ease both; }}
    .anim-fade {{ animation: fadeIn .5s ease both; }}
    .container > * {{ animation: fadeUp .5s ease both; }}
  </style>
</head>
<body>

<div class="cover">
  <div class="cover-tag">科研调研报告 · Research Report</div>
  <h1>{title}</h1>
  <div class="cover-meta">生成时间 &nbsp;/&nbsp; {generated_at}</div>
</div>

<div class="container">
{body_html}
</div>

<div class="footer">
  GENERATED BY LOCAL LLM RESEARCH AGENT &nbsp;·&nbsp; {generated_at}
</div>

</body>
</html>"""


class ReportRendererSkill:
    """
    报告渲染技能 - 作为 agent 可调度的 skill，与 RAGRetrieval / WebSearch 接口一致。
    executor 调用 skill.render(query, markdown) 即可生成 HTML 报告。
    """

    def __init__(self, reports_dir: str = None):
        if reports_dir is None:
            reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)
        print(f"报告渲染技能初始化完成 (输出目录: {self.reports_dir})")

    def render(self, user_query: str, markdown_content: str) -> str:
        """
        将 Markdown 报告渲染为 HTML 并保存。

        Args:
            user_query:       用户原始查询（用作标题和文件名）
            markdown_content: Markdown 格式的报告正文

        Returns:
            保存的 HTML 文件路径
        """
        return render_report(user_query, markdown_content, self.reports_dir)


def render_report(user_query: str, markdown_content: str, reports_dir: str) -> str:
    """
    将 Markdown 报告渲染为 HTML 并保存到 reports_dir。

    Args:
        user_query:       用户原始查询（用作文件名和标题）
        markdown_content: Markdown 格式的报告正文
        reports_dir:      报告保存目录

    Returns:
        保存的 HTML 文件路径
    """
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 清理查询字符串，用于文件名
    safe_query = re.sub(r'[^\w\u4e00-\u9fff]', '_', user_query)[:40]
    filename = f"{timestamp}_{safe_query}.html"
    filepath = os.path.join(reports_dir, filename)

    body_html = _md_to_html(markdown_content)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = _build_html(user_query, body_html, generated_at)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filepath
