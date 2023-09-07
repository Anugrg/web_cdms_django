
import numpy as np
import fiona
from shapely.geometry import shape


def get_asset_info(file: str) -> tuple:

    info = dict()
    print(file)

    try:
        sf = fiona.open(file, 'r')
    except Exception as e:
        return False, str(e), info

    sf_schema_prop = sf.schema['properties']

    # only allow string and int header
    allowed_header_types = ['int', 'str']
    allowed_headers = []
    header_values = dict()

    for header in sf_schema_prop:
        if sf_schema_prop[header].split(':')[0] in allowed_header_types:
            allowed_headers.append(header)
            header_values[header] = set()

    rec_count = 0

    for i, rec in enumerate(sf):

        try:
            if rec['geometry']['type'] not in ['MultiPolygon', 'Polygon']:
                raise ValueError('File contains non polygon record')

            shp = shape(rec['geometry'])

            if not shp.is_valid:
                raise ValueError(f'File contains invalid geometry at record no {i}')

        except Exception as e:

            return (False, str(e), info)

        for _header in allowed_headers:
            header_values[_header].add(rec['properties'][_header])

        rec_count = i + 1

    unique_headers = []

    for _header in allowed_headers:

        if len(header_values[_header]) == rec_count:
            unique_headers.append(_header)

    info['rec_count'] = rec_count
    info['unique_fields'] = unique_headers

    return True, None, info


def calc_rh(temp: np.ndarray, dewtemp: np.ndarray) -> np.ndarray:

    """
    Using, August–Roche–Magnus approximation
    RH = 100*( EXP( (17.625*TD) / (243.04+TD) ) / EXP( (17.625*T) / (243.04+T) ) )

    a = 17.625
    b = 243.04

    ** 6.1094 omitted cause will calculate fraction later
    es_td = (a*TD)/(b+TD)
    es_t  = (a*T) /(b+T)

    RH = 100*( exp(es_td) / exp(es_t) )
    """
    a = 17.625
    b = 243.04

    es_td = (a * dewtemp) / (b + dewtemp)
    es_t = (a * temp) / (b + temp)

    return 100 * (np.exp(es_td) / np.exp(es_t))

