import logging
import os
import shutil

import pandas as pd
from celery import shared_task
from celery.exceptions import Ignore
from celery.result import AsyncResult
from dwca import DarwinCoreArchive
from dwca.classes import Taxon, Occurrence
import dwca.terms as dwc
from xml_common.utils import Language as EMLLanguage

from apps.catalog.models import Kingdom, Division, ClassName, Order, Family, Genus, Species, Synonymy, \
    CATALOG_DWC_FIELDS, VernacularName, CommonName, Distribution, Region, SpeciesProfile
from apps.digitalization.models import HERBARIUM_DWC_FIELDS, VoucherImported
from apps.digitalization.storage_backends import PrivateMediaStorage
from apps.metadata.models import EML
from intranet.utils import HtmlLogger, close_process, TaskProcessLogger, GroupLogger


@shared_task(name='generate_dwc_archive', bind=True)
def generate_dwc_archive(self, option: int):
    error = None
    try:
        html_logger = HtmlLogger("DWC Archive")
        temp_folder = self.request.id
        os.makedirs(temp_folder, exist_ok=True)
        process_logger = TaskProcessLogger("DWC Archive", temp_folder)
        logger = GroupLogger("DWC Archive", html_logger, process_logger)
        try:
            eml = EML.objects.get(pk=option)
            logger.info(f"Generating EML file for {eml}")
            self.update_state(state="PROGRESS", meta={"step": 0, "total": 1, "logs": logger[0].get_logs()})
            darwin_core_archive = DarwinCoreArchive(eml.package_id)
            darwin_core_archive.__meta__.__metadata__ = "eml.xml"
            darwin_core_archive.__metadata__ = eml.eml_object
            if option == 1:
                logger.info(f"Generating Core Data File")
                self.update_state(state="PROGRESS", meta={"step": 0, "total": 1, "logs": logger[0].get_logs()})
                core = Taxon(
                    0, "taxon.tsv", CATALOG_DWC_FIELDS,
                    fields_terminated_by="\t", ignore_header_lines=1
                )
                kingdom_data = Kingdom.get_dwc_data(logger=logger, task=self)
                division_data = Division.get_dwc_data(logger=logger, task=self)
                class_data = ClassName.get_dwc_data(logger=logger, task=self)
                order_data = Order.get_dwc_data(logger=logger, task=self)
                family_data = Family.get_dwc_data(logger=logger, task=self)
                genus_data = Genus.get_dwc_data(logger=logger, task=self)
                species_data = Species.get_dwc_data(logger=logger, task=self)
                synonymy_data = Synonymy.get_dwc_data(logger=logger, task=self)
                results = pd.concat(
                    [
                        kingdom_data, division_data, class_data,
                        order_data, family_data, genus_data,
                        species_data, synonymy_data,
                    ]
                )
                logger.info("Adding core to archive")
                darwin_core_archive.core = core
                darwin_core_archive.core.pandas = results
                async_result = AsyncResult(self.request.id)
                current_total = async_result.info['total']
                # Extensions
                logger.info(f"Retrieving vernacular names")
                vernacular_extension = VernacularName(
                    0, "vernacular.tsv", [dwc.DWCLanguage(1), dwc.VernacularName(2)]
                )
                common_names_result = list()
                common_objects = CommonName.objects.all()
                for i, common_name in enumerate(common_objects):
                    self.update_state(state="PROGRESS", meta={"step": i + current_total, "total": current_total + common_objects.count(), "logs": logger[0].get_logs()})
                    for spp in common_name.species_set.all():
                        common_names_result.append([
                            spp.taxon_id, EMLLanguage.SPA, common_name.name_es
                        ])
                darwin_core_archive.extensions.append(vernacular_extension)
                darwin_core_archive.extensions[0].as_pandas(_no_interaction=True)
                darwin_core_archive.extensions[0].pandas = pd.DataFrame(common_names_result, columns=[fields.name for fields in vernacular_extension.__fields__])
                distribution_extension = Distribution(
                    0, "distribution.tsv", [dwc.OccurrenceStatus(1), dwc.DWCLocalityTerm(2), dwc.Country(3), dwc.CountryCode(4)]
                )
                distribution_results = list()
                regions = Region.objects.all()
                logger.info(f"Retrieving regions")
                current_total += regions.count()
                for i, region in enumerate(regions):
                    self.update_state(state="PROGRESS", meta={"step": i + current_total, "total": current_total + regions.count(), "logs": logger[0].get_logs()})
                    for spp in region.species_set.all():
                        distribution_results.append([
                            spp.taxon_id, dwc.OccurrenceStatus.DefaultStatus.PRESENT, region.name_es, "Chile", "CL"
                        ])
                darwin_core_archive.extensions.append(distribution_extension)
                darwin_core_archive.extensions[1].as_pandas(_no_interaction=True)
                darwin_core_archive.extensions[1].pandas = pd.DataFrame(distribution_results, columns=[fields.name for fields in distribution_extension.__fields__])
                # TODO: Species profile
                logger.info("Zipping archive")
                zip_filename = "catalog.zip"
                darwin_core_archive.to_file(zip_filename)
            else:
                logger.info(f"Generating Core Data File")
                self.update_state(state="PROGRESS", meta={"step": 0, "total": 1, "logs": logger[0].get_logs()})
                core = Occurrence(
                    0, "occurrence.tsv", HERBARIUM_DWC_FIELDS,
                    fields_terminated_by="\t", ignore_header_lines=1
                )
                herbarium_vouchers = VoucherImported.objects.filter(herbarium__metadata_id=option)
                results = herbarium_vouchers.get_dwc_data(logger=logger, task=self)
                logger.info("Adding core to archive")
                darwin_core_archive.core = core
                darwin_core_archive.core.pandas = results
                logger.info("Zipping archive")
                zip_filename = f"{eml.package_id}.zip"
                darwin_core_archive.to_file(zip_filename)
        except Exception as e:
            error = {
                "type": str(type(e)),
                "msg": str(e),
            }
            logger.error("Error generating DwC Archive")
            logger.error(e, exc_info=True)
            raise e
        finally:
            self.update_state(state='PROGRESS', meta={"step": 1, "total": 1, "logs": logger[0].get_logs()})
        logger[1].close()
        logger[1].save_file(PrivateMediaStorage(), temp_folder + ".log")
        close_process(logger[0], self, meta={"step": 1, "total": 1, }, error=error)
        shutil.rmtree(temp_folder)
        return "DwC Archive done"
    except Exception as e:
        logging.error(e, exc_info=True)
        logger[1].close()
        logger[1].save_file(PrivateMediaStorage(), temp_folder + ".log")
        close_process(logger[0], self, meta={"step": 1, "total": 1, }, error=error)
        shutil.rmtree(temp_folder)
        raise Ignore()
