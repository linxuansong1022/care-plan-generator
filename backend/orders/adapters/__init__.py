# adapters/__init__.py
from .cvs_web import CvsWebAdapter
from .clinic_b import ClinicBAdapter
from .pharmacorp import PharmaCorpAdapter
from .nordic import NordicHealthAdapter

def get_adapter(source: str):
    """工厂函数：根据数据来源返回对应的 adapter"""
    adapters = {
        "cvs_web": CvsWebAdapter,
        "clinic_b": ClinicBAdapter,
        "pharmacorp": PharmaCorpAdapter,
        "nordic": NordicHealthAdapter,
    }
    adapter_class = adapters.get(source)
    if not adapter_class:
        raise ValueError(f"Unknown source: '{source}'. Available: {list(adapters.keys())}")
    return adapter_class()
