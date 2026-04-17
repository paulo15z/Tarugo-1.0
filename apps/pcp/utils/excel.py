from io import BytesIO
import xlwt
import pandas as pd


def gerar_xls_roteiro(df: pd.DataFrame) -> BytesIO:
    """ gera arquivo XLS formatado com estilos """

    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Roteiro de Pecas')

    st_header = xlwt.easyxf(
        'font: bold true, colour white, height 200; '
        'pattern: pattern solid, fore_colour dark_blue; '
        'alignment: horiz centre, vert centre, wrap true; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_header_rot = xlwt.easyxf(
        'font: bold true, colour white, height 200; '
        'pattern: pattern solid, fore_colour dark_yellow; '
        'alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_data = xlwt.easyxf(
        'font: height 180; alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_data_alt = xlwt.easyxf(
        'font: height 180; pattern: pattern solid, fore_colour ice_blue; '
        'alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )
    st_rot = xlwt.easyxf(
        'font: bold true, height 180; pattern: pattern solid, fore_colour light_yellow; '
        'alignment: horiz centre, vert centre; '
        'borders: left thin, right thin, top thin, bottom thin;'
    )

    cols = list(df.columns)
    ws.row(0).height = 600

    for ci, col in enumerate(cols):
        st = st_header_rot if col in ('ROTEIRO', 'PLANO') else st_header
        ws.write(0, ci, col, st)
        ws.col(ci).width = 6000 if col in ('ROTEIRO', 'PLANO') else 4000

    for ri, (_, row) in enumerate(df.iterrows(), 1):
        st_base = st_data_alt if ri % 2 == 0 else st_data
        for ci, col in enumerate(cols):
            val = str(row.get(col, '')).replace('nan', '').strip()
            style = st_rot if col in ('ROTEIRO', 'PLANO') else st_base
            ws.write(ri, ci, val, style)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf