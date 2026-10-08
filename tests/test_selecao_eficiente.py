"""Seleção viável para 100 repositórios (auditoria S01, P1): contagem de runs que para no mínimo,
parada ao atingir a amostra e funil gravado de forma incremental."""

from datetime import date

from pipeline.config import SelecaoConfig
from pipeline.funil import renderizar_md
from pipeline.selection import contar_runs, selecionar


class Resp:
    def __init__(self, dados, headers=None):
        self.status_code, self._d, self.headers = 200, dados, headers or {}

    def json(self):
        return self._d


def test_contagem_de_runs_para_ao_atingir_o_minimo():
    chamadas = []

    class Api:
        def get(self, path, params=None):
            chamadas.append(params["created"])
            runs = [{"conclusion": "success"}] * 100  # 1ª página já tem >= 50 válidos
            return Resp({"total_count": 5000, "workflow_runs": runs},
                        {"Link": '<https://api.github.com/x?page=2>; rel="next"'})

    consultados, validos = contar_runs(Api(), "o/r", "main", date(2025, 1, 1), date(2025, 12, 31), minimo=50)
    assert validos >= 50
    assert len(chamadas) == 1  # nem subdividiu o mês no teto, nem pagina, nem olha os outros meses


def test_contagem_sem_minimo_continua_exata():
    class Api:
        def get(self, path, params=None):
            return Resp({"total_count": 3, "workflow_runs": [{"conclusion": "success"}, {"conclusion": "cancelled"},
                                                              {"conclusion": "failure"}]})

    consultados, validos = contar_runs(Api(), "o/r", "main", date(2025, 1, 1), date(2025, 2, 28))
    assert (consultados, validos) == (6, 4)  # 2 meses x (3 consultados, 2 válidos)


class ApiVarios:
    """30 repositórios que passam em todos os filtros."""

    def get(self, path, params=None):
        if path == "/search/repositories":
            itens = [{"full_name": f"o/r{i:02d}", "stargazers_count": 2000, "language": "Go",
                      "default_branch": "main", "created_at": "2020-01-01T00:00:00Z"} for i in range(30)]
            return Resp({"total_count": 30, "items": itens})
        if path.endswith("/actions/workflows"):
            return Resp({"total_count": 1})
        if path.endswith("/releases"):
            return Resp([{"draft": False, "prerelease": False, "published_at": f"2025-0{m}-10T00:00:00Z"} for m in range(1, 7)])
        if path.endswith("/actions/runs"):
            return Resp({"total_count": 60, "workflow_runs": [{"conclusion": "success"}] * 60})
        if path.endswith("/contributors"):
            return Resp([{}])
        raise AssertionError(path)


def test_para_ao_atingir_a_amostra_e_informa_nao_avaliados():
    parciais = []
    sel = SelecaoConfig(faixas_estrelas=(1000,))
    res = selecionar(ApiVarios(), sel, date(2025, 1, 1), date(2025, 12, 31),
                     ao_avaliar=lambda r: parciais.append(len(r.registros)), parar_em=12)
    assert len(res.registros) == 12 and res.candidatos_total == 30
    assert parciais == [10, 12]  # funil gravado a cada 10 e ao final
    md = renderizar_md(res)
    assert "12** candidatos avaliados" in md and "18** não avaliados" in md


def test_sem_parar_em_avalia_todos():
    res = selecionar(ApiVarios(), SelecaoConfig(faixas_estrelas=(1000,)), date(2025, 1, 1), date(2025, 12, 31))
    assert len(res.registros) == res.candidatos_total == 30
