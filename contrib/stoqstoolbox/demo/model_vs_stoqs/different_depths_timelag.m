      
    depth=[5,15,30,40]
    for i=1:4
        [model,insit]=model_vs_stoqs('http://ourocean.jpl.nasa.gov:8080/thredds/dodsC/MBNowcast/mb_das_2011062021.nc',depth(i),0.1,6,0);
        subplot(4,1,i)
        plot(insit.time,insit.vari,'-x');
        hold on;
        ext=extract_points(model,insit);
        plot(ext.modeltime,ext.pointdata,'.r');legend('Insitu measurement','Model value')
        datetick('x',15);
    end