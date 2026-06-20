import json
import copy

from pathlib import Path


BASE_DIR = Path(__file__).parent


def load_schema():

    schema_path = (

        BASE_DIR /

        "schema_device.json"

    )

    with open(

        schema_path,

        encoding="utf-8"

    ) as f:

        return json.load(f)


def apply_schema(

    llm_output

):

    schema = load_schema()

    devices = []

    for item in (

        llm_output.get(

            "devices",

            []

        )

    ):

        template = copy.deepcopy(

            schema[
                "devices"
            ][0]

        )


        if (

            "canonical_device_name"

            not in template

        ):

            template[
                "canonical_device_name"
            ] = ""


        for key, value in item.items():

            template[
                key
            ] = value



        if not template.get(

            "implant_status"

        ):

            template[
                "implant_status"
            ] = ""

        devices.append(

            template

        )

    schema[
        "devices"
    ] = devices

    return schema