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

from . import views
from .views import FinderApiView, MenuApiView, SpeciesDetails, GalleryList, BannerSpecie, \
    GeoSpeciesListApiView, GeoSpecimensListApiView
from .views import SynonymyDetails, DivisionList, ClassList, OrderList, SpecimensList
from .views import FamilyList, SpeciesListApiView
from .views import DistributionList, ImagesList, ImagesFilterApiView
from .views import ImageDetails, InfoApi, RegionList


urlpatterns = [
    re_path(r'^divisions/$', DivisionList.as_view()),
    re_path(r'^classes/$', ClassList.as_view()),
    re_path(r'^orders/$', OrderList.as_view()),
    re_path(r'^families/$', FamilyList.as_view()),
    re_path(r'^regions/$', RegionList.as_view()),
    re_path(r'^species/(?P<pk>\d+)/$', SpeciesDetails.as_view()),
    re_path(r'^synonymy/(?P<pk>\d+)/$', SynonymyDetails.as_view()),
    re_path(r'^specimens/$', SpecimensList.as_view()),
    re_path(r'^finder/(?P<text>[\w ]+)/$', FinderApiView.as_view()),
    re_path(r'^geo_species/$', GeoSpeciesListApiView.as_view()),
    re_path(r'^geo_specimens/$', GeoSpecimensListApiView.as_view()),
    re_path(r'^menu/$', MenuApiView.as_view()),
    re_path(r'^species_list/$', SpeciesListApiView.as_view()),
    re_path(r'^distribution/(?P<species_id>\d+)/$', DistributionList.as_view()),
    re_path(r'^images/(?P<species_id>\d+)/$', ImagesList.as_view()),
    re_path(r'^gallery/(?P<species_id>\d+)/$', GalleryList.as_view()),
    re_path(r'^images_filter/$', ImagesFilterApiView.as_view()),
    re_path(r'^image/(?P<pk>\d+)/$', ImageDetails.as_view()),
    re_path(r'^info/$', InfoApi.as_view()),
    re_path(r'^banner/(?P<specie_id>\d+)/$', BannerSpecie.as_view()),
    re_path(r'^names/$', views.get_names),
]
