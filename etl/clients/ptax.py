from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from etl.http import HttpClient

URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@di,dataFinalCotacao=@df)"


class Quote(BaseModel):
    cotacaoCompra: Decimal
    cotacaoVenda: Decimal
    dataHoraCotacao: str

    @property
    def rate_date(self) -> date:
        return datetime.strptime(self.dataHoraCotacao[:10], "%Y-%m-%d").date()


def fetch_period(http: HttpClient, start: date, end: date) -> list[Quote]:
    params = {"@di": f"'{start:%m-%d-%Y}'", "@df": f"'{end:%m-%d-%Y}'", "$format": "json"}
    data = http.get_json(URL, params)
    out = []
    for item in (data or {}).get("value", []):
        try:
            out.append(Quote.model_validate(item))
        except Exception:  # campo nulo/inesperado: ignora a linha e segue
            continue
    return out
