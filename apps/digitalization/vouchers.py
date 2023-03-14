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
            catalogNumber = row['catalogNumber']
            new_occurrence_id = self.__herbarium.institution_code + ':' + self.__herbarium.collection_code + ':' + f'{catalogNumber:07d}'
            code = BiodataCode(
                herbarium=self.__herbarium,
                code=new_occurrence_id,
                catalogNumber=row['catalogNumber'],
                created_by=self.__user,
                created_at=datetime.now(tz=pytz.timezone('America/Santiago')),
                qr_generated=False
            )
            code.save()
            if numpy.isnan(row['decimalLatitude']):
                decimalLatitude = None
            else:
                decimalLatitude = float(row['decimalLatitude'])
            if numpy.isnan(row['decimalLongitude']):
                decimalLongitude = None
            else:
                decimalLongitude = float(row['decimalLongitude'])

            try:
                organismRemarks = row['organismRemarks']
            except:
                organismRemarks = None

            try:
                identifiedBy = row['identifiedBy']
            except:
                identifiedBy = None

            try:
                dateIdentified = row['dateIdentified']
            except:
                dateIdentified = None

            try:
                verbatimElevation = int(row['verbatimElevation'])
            except:
                verbatimElevation = None
            try:
                priority_file = PriorityVouchersFile.objects.get(pk=self.__file_vouchers_id)
                specie = Species.objects.filter(scientificNameDB=row['scientificName'].strip())
                georeferencedDate = pandas.to_datetime(row['georeferencedDate'], infer_datetime_format=True,
                                                       format='%Y%m%d', utc=True)
                if pandas.isnull(georeferencedDate):
                    georeferencedDate = None
                if row['decimalLatitude'] and row['decimalLongitude']:
                    point = GEOSGeometry(
                        'POINT(' + str(row['decimalLongitude']) + ' ' + str(row['decimalLatitude']) + ')', srid=4326)
                    if not numpy.isnan(row['decimalLatitude']) and not numpy.isnan(row['decimalLongitude']):
                        decimalLatitude_public = self.public_point(row['decimalLatitude'])
                        decimalLongitude_public = self.public_point(row['decimalLongitude'])
                        point_public = GEOSGeometry(
                            'POINT(' + str(decimalLongitude_public) + ' ' + str(decimalLatitude_public) + ')',
                            srid=4326)
                    else:
                        point_public = None
                        decimalLatitude_public = None
                        decimalLongitude_public = None
                else:
                    point = None
                    point_public = None
                    decimalLatitude_public = None
                    decimalLongitude_public = None
                if row['priority']:
                    priority = row['priority']
                else:
                    priority = 1
                voucher_imported = VoucherImported(
                    vouchers_file=priority_file,
                    occurrenceID=code,
                    herbarium=self.__herbarium,
                    otherCatalogNumbers=row['otherCatalogNumbers'],
                    catalogNumber=row['catalogNumber'],
                    recordedBy=row['recordedBy'],
                    recordNumber=row['recordNumber'],
                    organismRemarks=organismRemarks,
                    scientificName=specie[0],
                    locality=row['locality'],
                    verbatimElevation=verbatimElevation,
                    georeferencedDate=georeferencedDate,
                    decimalLatitude=decimalLatitude,
                    decimalLongitude=decimalLongitude,
                    identifiedBy=identifiedBy,
                    dateIdentified=dateIdentified,
                    point=point,
                    decimalLatitude_public=decimalLatitude_public,
                    decimalLongitude_public=decimalLongitude_public,
                    point_public=point_public,
                    priority=priority
                )
                voucher_imported.save()
            except Exception as e:
                print(e)
                print(specie)
                print(row)
                data = '{"":{"0":null},"otherCatalogNumbers":{"0":' + str(
                    row['otherCatalogNumbers']) + '},"catalogNumber":{"0":' + str(
                    row['catalogNumber']) + '},"recordedBy":{"0":"' + str(
                    row['recordedBy']) + '"},"recordNumber":{"0":' + str(
                    row['recordNumber']) + '},"scientificName":{"0":"' + str(
                    row['scientificName'].strip()) + '"},"locality":{"0":"' + str(
                    row['locality']) + '"},"verbatimElevation":{"0":' + str(
                    verbatimElevation) + '},"georeferencedDate":{"0":"' + str(
                    row['georeferencedDate']) + '"},"decimalLatitude":{"0":' + str(
                    row['decimalLatitude']) + '},"decimalLongitude":{"0":' + str(row['decimalLongitude']) + '}}'
                return {'result': 'error', 'type': 'code', 'error': str(e), 'data': data}
        return {'result': 'ok'}

    def duplicate_number_in_import_file(self):
        return self.__data[self.__data.duplicated(['catalogNumber'], keep=False)]

    def duplicate_number_in_database(self):
        duplicates = []
        for index, row in self.__data.iterrows():
            voucher_imported = VoucherImported.objects.filter(herbarium=self.__herbarium,
                                                              catalogNumber=row['catalogNumber'])
            if voucher_imported:
                duplicates.append(row)
        return pandas.DataFrame(duplicates,
                                columns=['', 'otherCatalogNumbers', 'catalogNumber', 'recordedBy', 'recordNumber',
                                         'scientificName', 'locality', 'verbatimElevation', 'georeferencedDate',
                                         'decimalLatitude', 'decimalLongitude'])

    def validate_vouchers_in_catalog(self):
        invalid = []
        for index, row in self.__data.iterrows():
            specie = Species.objects.filter(scientificNameDB=row['scientificName'].strip())
            if not specie:
                similarity_values = Species.objects.annotate(
                    similarity=TrigramSimilarity('scientificNameDB', row['scientificName'].strip().upper()), ).filter(
                    similarity__gte=0.55).order_by('-similarity')
                if len(similarity_values) > 0:
                    if similarity_values[0].similarity < 1:
                        row['similarity'] = similarity_values[0].similarity
                        row['scientificName_similarity'] = similarity_values[0].scientificName
                        row['synonymy_similarity'] = ''
                        invalid.append(row)
                else:
                    similarity_values = Synonymy.objects.annotate(similarity=TrigramSimilarity('scientificNameDB', row[
                        'scientificName'].strip().upper()), ).filter(similarity__gte=0.55).order_by('-similarity')
                    if len(similarity_values) > 0:
                        row['similarity'] = similarity_values[0].similarity
                        specie_synonymy = Species.objects.filter(synonymys=similarity_values[0].id)
                        row['scientificName_similarity'] = specie_synonymy[0].scientificName
                        row['synonymy_similarity'] = similarity_values[0].scientificName
                    else:
                        row['similarity'] = 0
                        row['scientificName_similarity'] = ''
                        row['synonymy_similarity'] = ''
                    invalid.append(row)
        return pandas.DataFrame(invalid,
                                columns=['', 'otherCatalogNumbers', 'catalogNumber', 'recordedBy', 'recordNumber',
                                         'scientificName', 'locality', 'verbatimElevation', 'georeferencedDate',
                                         'decimalLatitude', 'decimalLongitude', 'scientificName_similarity',
                                         'similarity', 'synonymy_similarity'])

    def restore_db(self):
        for index, row in self.__data.iterrows():
            BiodataCode.objects.filter(catalogNumber=row['catalogNumber']).delete()
            VoucherImported.objects.filter(catalogNumber=row['catalogNumber']).delete()

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
                    r = '{"":{"0":null},"otherCatalogNumbers":{"0":''},"catalogNumber":{"0":''},"recordedBy":{"0":"''"},"recordNumber":{"0":''},"scientificName":{"0":"''"},"locality":{"0":"''"},"verbatimElevation":{"0":''},"georeferencedDate":{"0":"''"},"decimalLatitude":{"0":''},"decimalLongitude":{"0":''}}'
                    data = {'result': 'error', 'type': 'code', 'error': str(e), 'data': r}
            else:
                data = {'result': 'error', 'type': 'duplicates in file', 'data': duplicates_import_file.to_json()}
        except Exception as e:
            r = '{"":{"0":null},"otherCatalogNumbers":{"0":''},"catalogNumber":{"0":''},"recordedBy":{"0":"''"},"recordNumber":{"0":''},"scientificName":{"0":"''"},"locality":{"0":"''"},"verbatimElevation":{"0":''},"georeferencedDate":{"0":"''"},"decimalLatitude":{"0":''},"decimalLongitude":{"0":''}}'
            data = {'result': 'error', 'type': 'code', 'error': str(e), 'data': r}
            print(e)
        return (json.dumps(data))

    def __init__(self, file_vouchers, user):
        self.__data = pandas.read_excel(file_vouchers.file, header=0)
        self.__herbarium = file_vouchers.herbarium
        self.__file_vouchers_id = file_vouchers.id
        self.__user = user
