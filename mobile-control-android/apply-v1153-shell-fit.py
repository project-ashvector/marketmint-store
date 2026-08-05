from pathlib import Path
import re

path = Path('mobile-build/project/app/src/main/java/com/ebedesigns/marketmint/mobile/MainActivity.java')
text = path.read_text()

shell_css = r'''
        /* v1.15.3 shell reset: remove the desktop sidebar grid column on phones. */
        html.marketmint-mobile-shell,
        body.marketmint-mobile-app{
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
          overflow-x:hidden!important;
        }
        body.marketmint-mobile-app .shell{
          display:block!important;
          grid-template-columns:none!important;
          grid-template-rows:none!important;
          grid-auto-columns:auto!important;
          grid-auto-rows:auto!important;
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
          margin:0!important;
          padding:0!important;
          overflow-x:hidden!important;
        }
        body.marketmint-mobile-app .shell>.main,
        body.marketmint-mobile-app main.main,
        body.marketmint-mobile-app .main{
          position:relative!important;
          inset:auto!important;
          left:auto!important;
          right:auto!important;
          grid-column:1!important;
          grid-row:auto!important;
          float:none!important;
          transform:none!important;
          width:100%!important;
          min-width:0!important;
          max-width:100%!important;
          margin:0!important;
          box-sizing:border-box!important;
          overflow-x:hidden!important;
        }
        body.marketmint-mobile-app .shell>.sidebar{
          grid-column:auto!important;
          grid-row:auto!important;
        }
'''

css_match = re.search(
    r'(private static final String MOBILE_CSS = """\n)(.*?)(\n        """;)',
    text,
    flags=re.S,
)
if not css_match:
    raise SystemExit('MOBILE_CSS block was not found')
if 'v1.15.3 shell reset' not in css_match.group(2):
    css_body = css_match.group(2) + shell_css
    text = text[:css_match.start()] + css_match.group(1) + css_body + css_match.group(3) + text[css_match.end():]

for expected in (
    'v1.15.3 shell reset',
    'body.marketmint-mobile-app .shell{',
    'grid-template-columns:none!important;',
    'body.marketmint-mobile-app .shell>.main',
    'max-width:100%!important;',
    'overflow-x:hidden!important;',
):
    if expected not in text:
        raise SystemExit(f'Missing shell-fit change: {expected}')

path.write_text(text)
print('Removed desktop shell grid/sidebar column from mobile layout')
