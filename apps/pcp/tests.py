from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
import xlrd

from apps.pcp.repositories.tabela_exportacao_repository import TabelaExportacaoRepository
from apps.pcp.utils.excel import gerar_xls_roteiro


class TabelaExportacaoRepositoryTests(SimpleTestCase):
    def test_parseia_csv_padrao_para_pecas_operacionais(self):
        content = (
            "ID DA PECA;REFERENCIA DA PECA;DESCRICAO DA PECA;LOCAL;"
            "MATERIAL DA PECA;CODIGO DO MATERIAL;ESPESSURA;LARGURA DA PECA;"
            "ALTURA DA PECA;QUANTIDADE;BORDA_FACE_FRENTE;FURO A\n"
            "P1;MOD1-P1;Lateral esquerda;Cozinha;MDF Branco;MAT-01;18;500;700;2;Fita Branca;A123\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("exportacao.csv", content, content_type="text/csv")

        pecas = TabelaExportacaoRepository.parsear_arquivo(arquivo)

        self.assertEqual(len(pecas), 1)
        self.assertEqual(pecas[0].id_dinabox, "P1")
        self.assertEqual(pecas[0].descricao, "Lateral esquerda")
        self.assertEqual(pecas[0].modulo_nome, "Cozinha")
        self.assertEqual(pecas[0].quantidade, 2)
        self.assertEqual(str(pecas[0].dimensoes.espessura), "18")
        self.assertEqual(pecas[0].furacoes["A"], "A123")
        self.assertEqual(pecas[0].atributos_tecnicos, {})

    def test_preserva_dados_essenciais_do_csv(self):
        content = (
            "NOME DO CLIENTE;ID DO PROJETO;NOME DO PROJETO;DESCRICAO DO MODULO;"
            "ID DA PECA;REFERENCIA DA PECA;DESCRICAO DA PECA;LOCAL;"
            "MATERIAL DA PECA;CODIGO DO MATERIAL;ESPESSURA;LARGURA DA PECA;"
            "ALTURA DA PECA;QUANTIDADE\n"
            "Cliente X;12345;Projeto Y;Modulo Z;P1;MOD1-P1;Lateral esquerda;Cozinha;"
            "MDF Branco;MAT-01;18;500;700;2\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("exportacao.csv", content, content_type="text/csv")

        pecas = TabelaExportacaoRepository.parsear_arquivo(arquivo)

        self.assertEqual(len(pecas), 1)
        self.assertEqual(pecas[0].nome_do_cliente, "Cliente X")
        self.assertEqual(pecas[0].id_do_projeto, "12345")
        self.assertEqual(pecas[0].nome_do_projeto, "Projeto Y")
        self.assertEqual(pecas[0].descricao_modulo, "Modulo Z")

    def test_nao_repete_obs_duplicada(self):
        content = (
            "ID DA PECA;REFERENCIA DA PECA;DESCRICAO DA PECA;LOCAL;OBS;OBSERVACAO;"
            "ESPESSURA;LARGURA DA PECA;ALTURA DA PECA;QUANTIDADE\n"
            "P1;MOD1-P1;Lateral esquerda;Cozinha;Teste obs;Teste obs;18;500;700;1\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("exportacao.csv", content, content_type="text/csv")
        pecas = TabelaExportacaoRepository.parsear_arquivo(arquivo)

        self.assertEqual(len(pecas), 1)
        self.assertEqual(pecas[0].observacoes_original, "Teste obs")

    def test_gera_xls_real_com_todas_as_pecas(self):
        content = (
            "ID DA PECA;REFERENCIA DA PECA;DESCRICAO DA PECA;LOCAL;OBSERVACAO;"
            "ESPESSURA;LARGURA DA PECA;ALTURA DA PECA;QUANTIDADE\n"
            "P1;MOD1-P1;Lateral esquerda;Cozinha;Teste obs 1;18;500;700;1\n"
            "P2;MOD1-P2;Lateral direita;Cozinha;Teste obs 2;18;500;700;1\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("exportacao.csv", content, content_type="text/csv")
        pecas = TabelaExportacaoRepository.parsear_arquivo(arquivo)

        xls_bytes = gerar_xls_roteiro(pecas)

        self.assertTrue(xls_bytes.startswith(b"\xd0\xcf\x11\xe0"))
        workbook = xlrd.open_workbook(file_contents=xls_bytes)
        sheet = workbook.sheet_by_name("PCP")
        self.assertEqual(sheet.nrows, 3)
        self.assertEqual(sheet.cell_value(0, 0), "NOME DO CLIENTE")
        self.assertEqual(sheet.cell_value(0, 1), "ID DO PROJETO")
        self.assertEqual(sheet.cell_value(0, 2), "NOME DO PROJETO")
        self.assertEqual(sheet.cell_value(0, 3), "DESCRIÇÃO DO MÓDULO")
        self.assertEqual(sheet.cell_value(0, 19), "OBSERVACAO")
        self.assertEqual(sheet.cell_value(1, 19), "Teste obs 1")
        self.assertEqual(sheet.cell_value(2, 19), "Teste obs 2")
        self.assertEqual(sheet.cell_value(1, 7), "Lateral esquerda")
        self.assertEqual(sheet.cell_value(2, 7), "Lateral direita")
