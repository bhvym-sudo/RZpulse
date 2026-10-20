"""Verified operations only. No arbitrary URLs or mutations in this release."""
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PageQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    count: int = Field(25, ge=1, le=100)
    skip: int = Field(0, ge=0)
    from_: int | None = Field(None, alias="from", ge=946684800, le=4765046400)
    to: int | None = Field(None, ge=946684800, le=4765046400)


class OrderQuery(PageQuery):
    authorized: Literal[0, 1] | None = None
    receipt: str | None = Field(None, max_length=40)


@dataclass(frozen=True)
class Operation:
    resource: str
    name: str
    method: str
    path: str
    description: str
    documentation: str
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    authentication: str = "HTTP Basic (Payment Gateway key pair)"
    availability: str = "Account access to Payment Gateway resource required"
    read_only: bool = True

    def __post_init__(self):
        if self.method not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
            raise ValueError("Unsupported registry HTTP method.")
        if not re.fullmatch(r"/v[12]/[a-zA-Z0-9_/{}/-]+", self.path) or ".." in self.path:
            raise ValueError("Registry endpoints must be internal versioned API paths.")
        if set(re.findall(r"{(\w+)}", self.path)) != set(self.required):
            raise ValueError("Required path parameters do not match endpoint template.")
        if not self.documentation.startswith("https://razorpay.com/docs/"):
            raise ValueError("An official documentation reference is required.")

    def prepare(self, parameters: dict[str, Any]) -> tuple[str, dict]:
        params = dict(parameters)
        path = self.path
        for name in self.required:
            value = params.pop(name, "")
            prefix = {"payments": "pay", "orders": "order", "refunds": "rfnd",
                      "settlements": "setl"}[self.resource]
            if not isinstance(value, str) or not re.fullmatch(prefix + r"_[A-Za-z0-9]+", value):
                raise ValueError(f"Provide a valid {name} ({prefix}_…).")
            path = path.replace("{" + name + "}", value)
        if set(params) - set(self.optional):
            raise ValueError("Unsupported parameters for this operation.")
        if self.name == "list":
            model = OrderQuery if self.resource == "orders" else PageQuery
            try:
                if self.resource == "orders" and "authorized" in params:
                    params["authorized"] = int(params["authorized"])
                params = model.model_validate(params).model_dump(by_alias=True, exclude_none=True)
            except ValueError:
                raise ValueError("Invalid query: count 1–100, skip >=0, UNIX from/to; check fields.") from None
            if "from" in params and "to" in params and params["from"] > params["to"]:
                raise ValueError("from must be before to.")
        return path, params


REGISTRY: dict[str, Operation] = {}
for resource in ("payments", "orders", "refunds", "settlements"):
    for name in ("list", "fetch"):
        slug = "fetch-all-payments" if resource == "payments" else "fetch-all"
        doc = f"https://razorpay.com/docs/api/{resource}/{slug if name == 'list' else 'fetch-with-id'}/"
        op = Operation(resource, name, "GET", f"/v1/{resource}" + ("/{id}" if name == "fetch" else ""),
                       f"{'List one page of' if name == 'list' else 'Fetch one'} {resource}.", doc,
                       required=("id",) if name == "fetch" else (),
                       optional=(("count", "skip", "from", "to") +
                                 (("authorized", "receipt") if resource == "orders" else ()))
                       if name == "list" else ())
        REGISTRY[f"{resource}.{name}"] = op
