function s_array = dbconn_jdbc(database, sqlstr)
% Connect to STOQS databases, execute SQL string, and pass back structure array.
% Input   database: The database name on the server, e.g. stoqs_september2013_o
%         sqlstr  : SQL string, i.e. SELECT name FROM stoqs_platform
% Output  s_array   : structure array
%
% Example:
%   cout = dbconn_jdbc('stoqs_september2013_0', 'Select name from stoqs_parameter where standard_name LIKE 'sea%');
% 
% SQL may be copied from the STOQS UI and pasted into a Matlab string with: 
%   sql = clipboard('paste')
%   cout = dbconn_jdbc('stoqs_september2013_0', sql)
%
% **Note: The Java class path to the sqljdbc driver must be specified before call.
%         For best results put it in your classpath.txt file.  
%         Driver download :
%         http://www.microsoft.com/download/en/details.aspx?id=21599
%
% To make work for PostgreSQL/STOQS:
% 1. Download appropriate .jar file from http://jdbc.postgresql.org/download.html
% 2. Add the file to the static java classpath, e.g. on my system I added
%    /Users/mccann/Documents/MATLAB/postgresql-9.3-1100.jdbc4.jar to /Users/mccann/.matlab/R2012b/javaclasspath.txt 

import java.lang.Thread;
import java.lang.Class;
import java.sql.DriverManager;
import java.sql.ResultSetMetaData;
import java.sql.ResultSet;
current_thread = java.lang.Thread.currentThread();
class_loader = current_thread.getContextClassLoader();
class = java.lang.Class.forName('org.postgresql.Driver', false, class_loader);
database_url = ['jdbc:postgresql://kraken.shore.mbari.org/' database ]

try
    conn = java.sql.DriverManager.getConnection(database_url, 'everyone', 'guest');
   
    %# query database
    q = conn.prepareStatement(sqlstr);
    rs = q.executeQuery();

    rsMetaData=rs.getMetaData;
    colnum=rsMetaData.getColumnCount;
    
    % assign variables from resultset
    while (rs.next())
        
        % for each column in the resultset, load an array by the column name and type
        for cc=1:colnum
            eval(['iVal=rs.getString(',num2str(cc),');']); %get the column data as string type
            coltype=rsMetaData.getColumnTypeName(cc);      %assess the column type
            switch char(coltype)
                case {'int','decimal','float','double'} %check to see if a null value is passed, if so assign NaN
                    if ~isempty(iVal)
                        eval([deblank(char(rsMetaData.getColumnName(cc))),'(rs.getRow)=str2num(iVal);']);
                    else
                        eval([deblank(char(rsMetaData.getColumnName(cc))),'(rs.getRow)=NaN;']);
                    end
                otherwise %value is a string, so just pass it into the output array
                        eval([deblank(char(rsMetaData.getColumnName(cc))),'(rs.getRow)=cell(iVal);']);
            end %switch coltype
        end %for cc=1:colnum
        %make output array, cout
        for cc=1:colnum, 
          eval(['s_array.',char(rsMetaData.getColumnName(cc)),'=',char(rsMetaData.getColumnName(cc)),';']);
        end %for cc=1:colnum
    end %while rs.next
    % close all database connections
    try q.close();     catch, end
    try rs.close();     catch, end
    
catch
    msgbox(['Connection error occurred:' lasterr]);
    
end


