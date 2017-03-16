from loaders import dataloaders as dl
from BeautifulSoup import BeautifulSoup
import urllib.request, urllib.error, urllib.parse
from stoqs import models as m
urllist=[]
base_url='http://dods.mbari.org/opendap/data/auvctd/surveys/%(year)s/netcdf/'
##for year in range(2003, 2011):
for year in range(2010, 2011):
     text=BeautifulSoup(urllib.request.urlopen(base_url % {'year': year})).findAll(text=True)
     urllist += [(base_url+file) % {'year': year} for file in text if file.endswith('_decim.nc')]


##print "dl.ignored_names = %s" % str(dl.ignored_names)
for url in urllist:
    survey_name=url.rsplit('/')[-1].rsplit('_',2)[0]
    print(("Importing survey %s from url = %s" % (survey_name, url)))
    bl=dl.Base_Loader(survey_name, 
                       platform=m.Platform.objects.get(code='gulper'),
                       url=url,
                       stride=1)
    print("Calling process_data()...")
    bl.process_data()
