from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class AppInfo:
    rank: int
    dodagId: str
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __contains__(self, key: str) -> bool:
        return key in self.__dict__ or key in self.extra

    def __getitem__(self, key: str) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        elif key in self.extra:
            return self.extra[key]
        else:
            raise KeyError(f"key is not existed in AppInfo: {key}")
    
    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.__dict__ and key != "extra":
            self.__dict__[key] = value
        else:
            self.extra[key] = value

@dataclass
class NetInfo:
    srcIp: str
    dstIp: str
    hop_limit: int
    downward: bool
    extra: Dict[str, Any] = field(default_factory=dict)

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__ or key in self.extra

    def __getitem__(self, key: str) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        elif key in self.extra:
            return self.extra[key]
        else:
            raise KeyError(f"key is not existed in NetInfo: {key}")
    
    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.__dict__ and key != "extra":
            self.__dict__[key] = value
        else:
            self.extra[key] = value

@dataclass
class MacInfo:
    srcMac: str
    dstMac: str
    pending_bit: bool
    retriesLeft: Optional[int] = None
    seqnum: Optional[int] = None
    priority: Optional[bool] = None
    join_metric: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __contains__(self, key: str) -> bool:
        return key in self.__dict__ or key in self.extra

    def __getitem__(self, key: str) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        elif key in self.extra:
            return self.extra[key]
        else:
            raise KeyError(f"key is not existed in MacInfo: {key}")
    
    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.__dict__ and key != "extra":
            self.__dict__[key] = value
        else:
            self.extra[key] = value

@dataclass
class Packet:
    type: str
    mac: MacInfo
    app: Optional[AppInfo] = None
    net: Optional[NetInfo] = None
    pkt_len: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Packet":
        assert data.get("pkt_len", None) is not None

        mac_data = data.pop("mac", {})
        
        mac_defined_fields = {"srcMac", "dstMac", "pending_bit", "retriesLeft", "seqnum", "priority", "join_metric"}
        mac_extra = {k: v for k, v in mac_data.items() if k not in mac_defined_fields}
        mac_info = MacInfo(
            srcMac=mac_data.get("srcMac"),
            dstMac=mac_data.get("dstMac"),
            pending_bit=mac_data.get("pending_bit"),
            retriesLeft=mac_data.get("retriesLeft"),
            seqnum=mac_data.get("seqnum"),
            priority=mac_data.get("priority"),
            join_metric=mac_data.get("join_metric"),
            extra=mac_extra
        )

        app_info = None
        app_data = data.pop("app", None)
        if app_data:
            app_extra = {k: v for k, v in app_data.items() if k not in {"rank", "dodagId"}}
            app_info = AppInfo(
                rank=app_data.get("rank"),
                dodagId=app_data.get("dodagId"),
                extra=app_extra
            )

        net_info = None
        net_data = data.pop("net", None)
        if net_data:
            net_extra = {k: v for k, v in net_data.items() if k not in {"srcIp", "dstIp", "hop_limit", "downward"}}
            net_info = NetInfo(
                srcIp=net_data.get("srcIp"),
                dstIp=net_data.get("dstIp"),
                hop_limit=net_data.get("hop_limit"),
                downward=net_data.get("downward"),
                extra=net_extra
            )

        top_level_defined_fields = {"type", "app", "net", "mac", "pkt_len"}
        top_extra = {k: v for k, v in data.items() if k not in top_level_defined_fields}

        return cls(
            type=data.get("type"),
            mac=mac_info,
            app=app_info,
            net=net_info,
            pkt_len=data.get("pkt_len"),
            extra=top_extra
        )
    
    def __contains__(self, key: str) -> bool:
        return key in self.__dict__ or key in self.extra

    def __getitem__(self, key: str) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        elif key in self.extra:
            return self.extra[key]
        else:
            raise KeyError(f"key is not existed in Packet:{key}")
    
    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.__dict__ and key != "extra":
            self.__dict__[key] = value
        else:
            self.extra[key] = value
