#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime

import numpy
import pandas
import pytz
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.postgres.search import TrigramSimilarity

from apps.catalog.models import Species, Synonymy
from .models import VoucherImported, BiodataCode, PriorityVouchersFile


class PriorityVouchers:

    def public_point(self, point):
        integer = int(point)
        min_grade = point - integer
        min = min_grade * 60
        min_round = round(min) - 1
        public_point = integer + min_round / 60
        return (public_point)

    def import_data(self):
        for index, row in self.__data.iterrows():
            catalog_number = row['catalog_number']
            new_occurrence_id = self.__herbarium.institution_code + ':' + self.__herbarium.collection_code + ':' + f'{catalog_number:07d}'
            code = BiodataCode(
                herbarium=self.__herbarium,
                code=new_occurrence_id,
                catalog_number=row['catalog_number'],
                created_by=self.__user,
                created_at=datetime.now(tz=pytz.timezone('America/Santiago')),
                qr_generated=False
            )
            code.save()
            if numpy.isnan(row['decimal_latitude']):
                decimal_latitude = None
            else:
                decimal_latitude = float(row['decimal_latitude'])
            if numpy.isnan(row['decimal_longitude']):
                decimal_longitude = None
            else:
                decimal_longitude = float(row['decimal_longitude'])

            try:
                organism_remarks = row['organism_remarks']
            except:
                organism_remarks = None

            try:
                identified_by = row['identified_by']
            except:
                identified_by = None

            try:
                identified_date = row['identified_date']
            except:
                identified_date = None

            try:
                verbatim_elevation = int(row['verbatim_elevation'])
            except:
                verbatim_elevation = None
            try:
                priority_file = PriorityVouchersFile.objects.get(pk=self.__file_vouchers_id)
                specie = Species.objects.filter(scientific_name_db=row['scientific_name'].strip())
                georeference_date = pandas.to_datetime(row['georeference_date'], infer_datetime_format=True,
                                                       format='%Y%m%d', utc=True)
                if pandas.isnull(georeference_date):
                    georeference_date = None
                if row['decimal_latitude'] and row['decimal_longitude']:
                    point = GEOSGeometry(
                        'POINT(' + str(row['decimal_longitude']) + ' ' + str(row['decimal_latitude']) + ')', srid=4326)
                    if not numpy.isnan(row['decimal_latitude']) and not numpy.isnan(row['decimal_longitude']):
                        decimal_latitude_public = self.public_point(row['decimal_latitude'])
                        decimal_longitude_public = self.public_point(row['decimal_longitude'])
                        point_public = GEOSGeometry(
                            'POINT(' + str(decimal_longitude_public) + ' ' + str(decimal_latitude_public) + ')',
                            srid=4326)
                    else:
                        point_public = None
                        decimal_latitude_public = None
                        decimal_longitude_public = None
                else:
                    point = None
                    point_public = None
                    decimal_latitude_public = None
                    decimal_longitude_public = None
                if row['priority']:
                    priority = row['priority']
                else:
                    priority = 1
                voucher_imported = VoucherImported(
                    vouchers_file=priority_file,
                    biodata_code=code,
                    herbarium=self.__herbarium,
                    other_catalog_numbers=row['other_catalog_numbers'],
                    catalog_number=row['catalog_number'],
                    recorded_by=row['recorded_by'],
                    record_number=row['record_number'],
                    organism_remarks=organism_remarks,
                    scientific_name=specie[0],
                    locality=row['locality'],
                    verbatim_elevation=verbatim_elevation,
                    georeference_date=georeference_date,
                    decimal_latitude=decimal_latitude,
                    decimal_longitude=decimal_longitude,
                    identified_by=identified_by,
                    identified_date=identified_date,
                    point=point,
                    decimal_latitude_public=decimal_latitude_public,
                    decimal_longitude_public=decimal_longitude_public,
                    point_public=point_public,
                    priority=priority
                )
                voucher_imported.save()
            except Exception as e:
                print(e)
                print(specie)
                print(row)
                data = '{"":{"0":null},"other_catalog_numbers":{"0":' + str(
                    row['other_catalog_numbers']) + '},"catalog_number":{"0":' + str(
                    row['catalog_number']) + '},"recorded_by":{"0":"' + str(
                    row['recorded_by']) + '"},"record_number":{"0":' + str(
                    row['record_number']) + '},"scientific_name":{"0":"' + str(
                    row['scientific_name'].strip()) + '"},"locality":{"0":"' + str(
                    row['locality']) + '"},"verbatim_elevation":{"0":' + str(
                    verbatim_elevation) + '},"georeference_date":{"0":"' + str(
                    row['georeference_date']) + '"},"decimal_latitude":{"0":' + str(
                    row['decimal_latitude']) + '},"decimal_longitude":{"0":' + str(row['decimal_longitude']) + '}}'
                return {'result': 'error', 'type': 'code', 'error': str(e), 'data': data}
        return {'result': 'ok'}

    def duplicate_number_in_import_file(self):
        return self.__data[self.__data.duplicated(['catalog_number'], keep=False)]

    def duplicate_number_in_database(self):
        duplicates = []
        for index, row in self.__data.iterrows():
            voucher_imported = VoucherImported.objects.filter(herbarium=self.__herbarium,
                                                              catalog_number=row['catalog_number'])
            if voucher_imported:
                duplicates.append(row)
        return pandas.DataFrame(duplicates,
                                columns=['', 'other_catalog_numbers', 'catalog_number', 'recorded_by', 'record_number',
                                         'scientific_name', 'locality', 'verbatim_elevation', 'georeference_date',
                                         'decimal_latitude', 'decimal_longitude'])

    def validate_vouchers_in_catalog(self):
        invalid = []
        for index, row in self.__data.iterrows():
            specie = Species.objects.filter(scientific_name_db=row['scientific_name'].strip())
            if not specie:
                similarity_values = Species.objects.annotate(
                    similarity=TrigramSimilarity('scientific_name_db', row['scientific_name'].strip().upper()), ).filter(
                    similarity__gte=0.55).order_by('-similarity')
                if len(similarity_values) > 0:
                    if similarity_values[0].similarity < 1:
                        row['similarity'] = similarity_values[0].similarity
                        row['scientific_name_similarity'] = similarity_values[0].scientific_name
                        row['synonymy_similarity'] = ''
                        invalid.append(row)
                else:
                    similarity_values = Synonymy.objects.annotate(similarity=TrigramSimilarity('scientific_name_db', row[
                        'scientific_name'].strip().upper()), ).filter(similarity__gte=0.55).order_by('-similarity')
                    if len(similarity_values) > 0:
                        row['similarity'] = similarity_values[0].similarity
                        specie_synonymy = Species.objects.filter(synonyms=similarity_values[0].id)
                        row['scientific_name_similarity'] = specie_synonymy[0].scientific_name
                        row['synonymy_similarity'] = similarity_values[0].scientific_name
                    else:
                        row['similarity'] = 0
                        row['scientific_name_similarity'] = ''
                        row['synonymy_similarity'] = ''
                    invalid.append(row)
        return pandas.DataFrame(invalid,
                                columns=['', 'other_catalog_numbers', 'catalog_number', 'recorded_by', 'record_number',
                                         'scientific_name', 'locality', 'verbatim_elevation', 'georeference_date',
                                         'decimal_latitude', 'decimal_longitude', 'scientific_name_similarity',
                                         'similarity', 'synonymy_similarity'])

    def restore_db(self):
        for index, row in self.__data.iterrows():
            BiodataCode.objects.filter(catalog_number=row['catalog_number']).delete()
            VoucherImported.objects.filter(catalog_number=row['catalog_number']).delete()

    def import_to_db(self):
        try:
            duplicates_import_file = self.duplicate_number_in_import_file()
            if len(duplicates_import_file) == 0:
                try:
                    duplicates_database = self.duplicate_number_in_database()
                    if len(duplicates_database) == 0:
                        valids = self.validate_vouchers_in_catalog()
                        if len(valids) == 0:
                            data = self.import_data()
                            if data['result'] == 'error':
                                self.restore_db()
                        else:
                            data = {'result': 'error', 'type': 'no match with catalog', 'data': valids.to_json()}
                    else:
                        data = {'result': 'error', 'type': 'duplicates in database',
                                'data': duplicates_database.to_json()}
                except Exception as e:
                    r = '{"":{"0":null},"other_catalog_numbers":{"0":''},"catalog_number":{"0":''},"recorded_by":{"0":"''"},"record_number":{"0":''},"scientific_name":{"0":"''"},"locality":{"0":"''"},"verbatim_elevation":{"0":''},"georeference_date":{"0":"''"},"decimal_latitude":{"0":''},"decimal_longitude":{"0":''}}'
                    data = {'result': 'error', 'type': 'code', 'error': str(e), 'data': r}
            else:
                data = {'result': 'error', 'type': 'duplicates in file', 'data': duplicates_import_file.to_json()}
        except Exception as e:
            r = '{"":{"0":null},"other_catalog_numbers":{"0":''},"catalog_number":{"0":''},"recorded_by":{"0":"''"},"record_number":{"0":''},"scientific_name":{"0":"''"},"locality":{"0":"''"},"verbatim_elevation":{"0":''},"georeference_date":{"0":"''"},"decimal_latitude":{"0":''},"decimal_longitude":{"0":''}}'
            data = {'result': 'error', 'type': 'code', 'error': str(e), 'data': r}
            print(e)
        return (json.dumps(data))

    def __init__(self, file_vouchers, user):
        self.__data = pandas.read_excel(file_vouchers.file, header=0)
        self.__herbarium = file_vouchers.herbarium
        self.__file_vouchers_id = file_vouchers.id
        self.__user = user
