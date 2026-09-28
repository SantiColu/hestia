from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Base of every model exposed by the API.

    Fields with defaults are always present in responses, so the contract marks them required
    in output schemas and generated clients do not have to handle ``undefined``.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
