"""intranet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import re_path

from .views import index, InfoApi, DivisionList, ClassList, OrderList, FamilyList, GenusList, RetrieveTaxaApiView, \
    RequestDownload
from .views import PlantHabitList, EnvHabitList, StatusList, CycleList, RegionList, ConservationStatusList, \
    CommonNameList
from .views import MenuApiView, NameApiView, FinderApiView, RegionDetails, SpeciesListApiView, SpeciesDetails, \
    SynonymyDetails, DistributionList, SpecimensList, SpecimenDetails

urlpatterns = [
    re_path(r'^$', index, name='index'),
    re_path(r'^info/$', InfoApi.as_view()),
    re_path(r'^divisions/$', DivisionList.as_view()),
    re_path(r'^classes/$', ClassList.as_view()),
    re_path(r'^orders/$', OrderList.as_view()),
    re_path(r'^families/$', FamilyList.as_view()),
    re_path(r'^genus/$', GenusList.as_view()),
    re_path(r'^plant_habit/$', PlantHabitList.as_view()),
    re_path(r'^env_habit/$', EnvHabitList.as_view()),
    re_path(r'^status/$', StatusList.as_view()),
    re_path(r'^cycles/$', CycleList.as_view()),
    re_path(r'^regions/$', RegionList.as_view()),
    re_path(r'^conservation_status/$', ConservationStatusList.as_view()),
    re_path(r'^common_names/$', CommonNameList.as_view()),
    re_path(r'^menu/$', MenuApiView.as_view()),
    re_path(r'^names/$', NameApiView.as_view()),
    re_path(r'^finder/(?P<text>[\w ]+)/$', FinderApiView.as_view()),
    re_path(r'^region/(?P<pk>\d+)/$', RegionDetails.as_view()),
    re_path(r'^species_list/$', SpeciesListApiView.as_view()),
    re_path(r'^taxa/(?P<unique_taxon_id>\d+)/$', RetrieveTaxaApiView.as_view()),
    re_path(r'^species/(?P<unique_taxon_id>\d+)/$', SpeciesDetails.as_view()),
    re_path(r'^synonymy/(?P<unique_taxon_id>\d+)/$', SynonymyDetails.as_view()),
    re_path(r'^distribution/(?P<species_id>\d+)/$', DistributionList.as_view()),
    re_path(r'^specimens_list/$', SpecimensList.as_view()),
    re_path(r'^specimen/(?P<pk>\d+)/$', SpecimenDetails.as_view()),
    # re_path(r'^banner/(?P<specie_id>\d+)/$', BannerSpecie.as_view()),
    re_path(r'^download_species_list/$', RequestDownload.as_view()),
]
