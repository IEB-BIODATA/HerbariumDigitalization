from django.contrib import admin

from apps.metadata.forms import GeographicCoverageForm
from apps.metadata.models import GeographicCoverage, TaxonomicCoverage, TaxonomicClassification, ResponsibleParty, \
    Keyword, Method, ProcedureStep, EMLDataset, EML, KeywordSet, TaxonID


@admin.register(GeographicCoverage)
class GeographicCoverageAdmin(admin.ModelAdmin):
    form = GeographicCoverageForm
    list_display = (['description'])


@admin.register(TaxonID)
class TaxonIDAdmin(admin.ModelAdmin):
    list_display = (['taxon_id', 'provider'])


@admin.register(TaxonomicClassification)
class TaxonomicClassificationAdmin(admin.ModelAdmin):
    list_display = (['rank_name', 'rank_value', 'common_name', 'parent'])


@admin.register(TaxonomicCoverage)
class TaxonomicCoverageAdmin(admin.ModelAdmin):
    list_display = (['general'])


@admin.register(ResponsibleParty)
class ResponsiblePartyAdmin(admin.ModelAdmin):
    list_display = (['name', 'last_name', 'position', 'organization'])


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = (['keyword', 'type'])


@admin.register(KeywordSet)
class KeywordSetAdmin(admin.ModelAdmin):
    list_display = (['display_keywords', 'thesaurus'])

    def display_keywords(self, obj):
        return ", ".join([keyword.keyword for keyword in obj.keywords.all()])


@admin.register(Method)
class MethodAdmin(admin.ModelAdmin):
    list_display = (['pk'])


@admin.register(ProcedureStep)
class ProcedureStepAdmin(admin.ModelAdmin):
    list_display = (['step'])


@admin.register(EMLDataset)
class EMLDatasetAdmin(admin.ModelAdmin):
    list_display = (['title'])


@admin.register(EML)
class EMLAdmin(admin.ModelAdmin):
    list_display = (['package_id'])
