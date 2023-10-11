"""web URL Configuration

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
from .views import SpeciesList, FinderApiView, MenuApiView, SpeciesDetails, GalleryList, BannerSpecie
from .views import SynonymyDetails, DivisionList, ClassList, OrderList
from .views import FamilyList, SpeciesFilterApiView, MenuFilterApiView
from .views import DistributionList, ImagesList, ImagesFilterApiView
from .views import ImagesCountApiView, ImageDetails, TotalImages, TotalSpecies, RegionList

urlpatterns = [
    re_path(r'^divisions/(?P<limit>\d+)/$', DivisionList.as_view()),
    re_path(r'^classes/(?P<limit>\d+)/$', ClassList.as_view()),
    re_path(r'^orders/(?P<limit>\d+)/$', OrderList.as_view()),
    re_path(r'^families/(?P<limit>\d+)/$', FamilyList.as_view()),
    re_path(r'^regions/(?P<limit>\d+)/$', RegionList.as_view()),
    re_path(r'^species/(?P<specie_name>[\w ]+)/$', SpeciesList.as_view()),
    re_path(r'^specie/(?P<specie_id>\d+)/$', SpeciesDetails.as_view()),
    re_path(r'^synonymy/(?P<synonymy_id>\d+)/$', SynonymyDetails.as_view()),
    re_path(r'^finder/(?P<category>[\w ]+)/(?P<word>[\w ]+)/$', FinderApiView.as_view()),
    re_path(r'^menu/$', MenuApiView.as_view()),
    re_path(r'^species_filter/$', SpeciesFilterApiView.as_view()),
    re_path(r'^menu_filter/(?P<limit>\d+)/$', MenuFilterApiView.as_view()),
    re_path(r'^distribution/(?P<specie_id>\d+)/$', DistributionList.as_view()),
    re_path(r'^images/(?P<specie_id>\d+)/$', ImagesList.as_view()),
    re_path(r'^gallery/(?P<specie_id>\d+)/$', GalleryList.as_view()),
    re_path(r'^images_filter/$', ImagesFilterApiView.as_view()),
    re_path(r'^images_count/$', ImagesCountApiView.as_view()),
    re_path(r'^image/(?P<voucher_id>\d+)/$', ImageDetails.as_view()),
    re_path(r'^total_images/$', TotalImages.as_view()),
    re_path(r'^total_species/$', TotalSpecies.as_view()),
    re_path(r'^banner/(?P<specie_id>\d+)/$', BannerSpecie.as_view()),
    re_path(r'^names/$', views.get_names, name='get_names'),
    re_path(r'^login$', views.login, name='login'),
]
