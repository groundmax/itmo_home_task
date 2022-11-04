import typing as tp

from rectools.metrics import MAP, Precision, Recall

RECO_SIZE: tp.Final = 10

METRICS: tp.Final = {
    "Precision@10": Precision(k=RECO_SIZE),
    "Recall@10": Recall(k=RECO_SIZE),
    "MAP@10": MAP(k=RECO_SIZE),
}
