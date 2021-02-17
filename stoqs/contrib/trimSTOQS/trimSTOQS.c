/***************  trimSTOQS.c -- brent@mbari.org  ***************
*    Copyright (C) 2019 MBARI
*    MBARI Proprietary Information. All rights reserved.
*
* CSV or TSV files output by MBARI's STOQS database contain one line
* for each parameter value extracted.  Each of these lines repeats the
* same contextual data (sample time, depth, etc.)
* This utility reformates this output file so that each line output
* includes all the parameters of interest.
* Contextual data *is not* repeated on adjacent lines.
*
******************************************************************/

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdbool.h>
#include <getopt.h>   //for getopt_long()
#include <stdarg.h>
#include <ctype.h>
#include <limits.h>
#include <time.h>
#include <libgen.h>   //for basename()

#define elementsIn(array) (sizeof(array)/sizeof(array[0]))
#define maxFields 99
#define maxLineLen 2000

struct map {
  size_t indices;
  size_t index[maxFields];
};
typedef char tableLine[maxLineLen];

static char *progName;

//command options
static char debug = 0;
static char *separator = "\t";
static char *outputSeparator = ",";

//default fields
static const char *commonEnv = "timevalue,depth,geom.x,geom.y";
static const char *extraEnv = "platform__name";
static const char *valueEnv = "datavalue";
static struct map commonMap, extraMap;  //corresponding column output order

static tableLine header;  //reversed field names
static size_t hdrFields;  //number of fields in header
                        //pointers to reversed field names
static char *revField[maxFields+1];

static unsigned lineno = 0;  //input line number

static tableLine inLine, outLine;     //input and output line buffers
static tableLine initialNames, names; //data parameter names in each block
static tableLine extraLine;  //extra line buffer (scratchpad)

static void usage(void)
{
  printf ("%s revised 9/17/19 brent@mbari.org\n", progName);
  printf (
"Trim a TSV (or CSV) file output by MBARI STOQS.\n"
"Reads output from STOQS on stdin.  Writes trimmed result to stdout. Usage:\n"
"  %s [nameColumn] {options}\n"
"nameColumn selects which field stores names of datavalues\n"
"Columns or Fields are identified by index (0..n) or suffix from column names\n"
"Options:  (may be abbriviated)\n"
"  --separator='\\t'         #input column separator\n"
"  --outputSeparator=,      #output column separator\n"
"  --debug{=level}          #enable debug messages {at optional level number}\n"
"  --help                   #displays this\n"
"Examples:\n"
"  %s name <stoqsHuge.tsv >trimmed.csv\n"
"  %s standard_name --separator=, <stoqsHuge.csv >trimmed.csv\n"
"  %s name --separator=, --outputSep='\\t' <stoqsHuge.csv >trimmed.tsv\n"
"Environment Variable:\n"
"  common=%s	#common columns/fields\n"
"  value=%s #name of column containing data value\n"
"  extra=%s	#extra unchanging columns/fields\n",
  progName, progName, progName, progName, commonEnv, valueEnv, extraEnv);
}


static void syntaxErr(char *format, ...)
{
  va_list ap;
  va_start(ap, format);
  vfprintf(stderr, format, ap);
  va_end(ap);
  fprintf(stderr, "\nTry running '%s -help'\n", progName);
  exit(3);
}

static void unescape(char *s)
/*
   replace 'C' escape sequences in s with the char values they represent
   works in place.
   Does not handle Unicode
*/
{
  char *out = s;
  int c;
  while (c=*s++) {
    if (c == '\\')
      switch (c=*s++) {
        case 'a':
          c = '\a';
          break;
        case 'b':
          c = '\b';
          break;
        case 'e':
          c = '\e';
          break;
        case 'f':
          c = '\f';
          break;
        case 'n':
          c = '\n';
          break;
        case 'r':
          c = '\r';
          break;
        case 't':
          c = '\t';
          break;
        case 'v':
          c = '\v';
          break;
        case '0':
          c = strtoul(s, &s, 8);
          break;
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6':
        case '7':
        case '8':
        case '9':
          c = strtoul(s-1, &s, 10);
          break;
        case 'x':
          c = strtoul(s, &s, 16);
      }
    *out++ = c;
  }
  *out='\0';
}

static void reverse(char *s)
//reverse s in place
{
  char *end = s+strlen(s);
  while (end > s) {
    char c = *s;
    *s++ = *--end;
    *end = c;
  }
}

static char *parseInt(const char *cursor, int *integer)
// parse an integer at cursor
// returns pointer to next char
//  abort with a syntaxErr if no valid text found
{
  char *end;
  long result;
  errno = 0;
  result = strtol(cursor, &end, 0);
  if (errno || end==cursor || result < INT_MIN || result > INT_MAX)
    syntaxErr("\"%s\" is not a valid integer", cursor);
  *integer = result;
  return end;
}

static void parseHeader(void)
//parse header as series of column names
//column names are reversed in place to facilitate matching suffixes
{
  char *fieldName, *hidden, *hdr = header;
  hdrFields = 0;
  while (fieldName=strtok_r(hdr, separator, &hidden)) {
    if (hdrFields >= elementsIn(revField)-1)
      syntaxErr("Too many data fields (>%d)", elementsIn(revField)-1);
    reverse(fieldName);
    revField[hdrFields++] = fieldName;
    hdr = NULL;
  }
  revField[hdrFields] = NULL;
}

static bool loadLine(FILE *in, tableLine line)
//load one line as series of column strings
//returns true unless error or end of file.
//strips trailing control chars.
{
  char *ok = fgets(line, sizeof(tableLine), stdin);
  if (!ok) {
    line[0] = '\0';
    return false;
  }
  char *end = line + strlen(line);
  while (--end >= line && (unsigned)(*end) <= ' ') ;
  end[1] = '\0';
  lineno++;
  return true;
}

static const char *fieldStart(const char *s, size_t index, int sep)
//return pointer to first charcater of index'th field by counting separators
//NULL if end of s reached
{
  for(;s && index; --index, s++)
    s = strchr(s, sep);
  return s;
}

static const char *fieldEnd(const char *s, int sep)
{
  int c;
  while ((c = *s) && c != sep)
    s++;
  return s;
}

static size_t parseField(const char *id, size_t suffixLen)
//return index of field selected by id
//id may be unsigned number or the suffix of a field name in header
{
  int index;
  if (isdigit(id[0])) {
    parseInt(id, &index);
    if (index < 0 || index >= hdrFields)
      syntaxErr("Field number (%d) out of range (0..%d)", index, hdrFields-1);
  }else{
    tableLine buf;
    char **reversed = &revField[0];
    memcpy(buf, id, suffixLen);
    buf[suffixLen]='\0';
    reverse(buf);
    while (*reversed) {
      if (!strncasecmp(*reversed, buf, suffixLen)) {
        index = reversed - revField;
        if (debug)
          fprintf(stderr, "%.*s[%d]\n", (int)suffixLen, id, index);
        return index;
      }
      reversed++;
    }
    syntaxErr("There is no field whose name ends with `%s\'", id);
  }
  return index;
}


static size_t parseMap(const char *fieldList, struct map *map)
//resolve comma seperated fieldList to fieldMap table of column indices
{
  const char *cursor = fieldList;
  int c;
  map->indices = 0;
  while (c = *cursor) {
    if (c == ',')
      cursor++;
    else{
      if (map->indices >= maxFields)
        syntaxErr("Too many output fields (>%d)", maxFields);
      const char *id = cursor++;
      while((c = *cursor) && c != ',')
        cursor++;
      map->index[map->indices++] = parseField(id, cursor-id);
    }
  }
  if (debug>1) {
    for(size_t i=0; i<map->indices-1; i++)
      fprintf(stderr, "%d,", (int)(map->index[i]));
    fprintf(stderr, "%d\n", (int)(map->index[map->indices-1]));
  }
}


static void putMap(FILE *output, const char *cursor)
/*
   output parameter names, each followed by output separator
*/
{
  int c;
  while (c = *cursor) {
    if (c == ',')
      cursor++;
    else{
      const char *id = cursor++;
      while((c = *cursor) && c != ',')
        cursor++;
      fprintf(output, "%.*s%c", (int)(cursor-id), id, *outputSeparator);
    }
  }
}


static char *addString(const char *start, int delim, char *out, char *end)
/*
  add string at start ended by delim character to out
  end points to the end of the out buffer (for overflow detection)
  returns out pointer past outputSeparator appended
  does not terminate string
*/
{
  if (!start)
    syntaxErr("Line #%u missing required field", lineno);
  size_t fieldLen = fieldEnd(start, delim) - start;
  if (out + fieldLen + 1 >= end)
    syntaxErr("Output line #%u too long", lineno);
  memcpy(out, start, fieldLen);
  out += fieldLen;
  *out++ = *outputSeparator;
  return out;
}


static char *addField(const tableLine input, size_t index, char *out, char *end)
/*
  add index field of input to out
  end points to the end of the out buffer (for overflow detection)
  returns out pointer past outputSeparator appended
  does not terminate string
*/
{
  int sep = *separator;
  return addString(fieldStart(input, index, sep), sep, out, end);
}


static char *remap(struct map *map, const tableLine input, tableLine output)
/*
  remap fields from input into output line buffer
  returns pointer to end of output string
*/
{
  char *out = &output[0];
  char *end = out + sizeof(tableLine);
  size_t outFields = map->indices;
  if (outFields) {
    const char *in = &input[0];
    size_t col = 0;
    do
      out = addField(input, map->index[col], out, end);
    while (++col < outFields);
    --out;  //overwrite trailing separator
  }
  *out = '\0';
  return out;
}


static char *extractCommon(const tableLine input, tableLine output)
/*
   extract context fields in input to output line with trailing separator
   returns pointer to end of output string
*/
{
  char *out = remap(&commonMap, input, output);
  if (out != output) {  //replace trailing separator
    *out++ = *outputSeparator;
    *out = '\0';
  }
  return out;
}


static ssize_t findName(const char *list, const char *key, size_t keyLen)
/*
   return the index key in list of keys separated by *outputSeparator
   return -1 if key not found in list
*/
{
  int sep = *outputSeparator;
  ssize_t index = 0;
  if (*list) for(;;) {
    size_t len = fieldEnd(list, sep) - list;
    if (len == keyLen && !memcmp(list, key, keyLen))
      return index;
    index++;
    list += len;
    if (!*list)
      break;
    list++;
  }
  return -1;
}


static char *nextBlock(tableLine output, tableLine names, tableLine input,
                       FILE *in, size_t valueIndex, size_t nameIndex)
/*
   Read first line from input buffer, subsequent lines form in file.
   Continue reading lines from in file until one of the context fields changes.
   Ignore blank lines.
   valueIndex = index of column containing parameter to append to common context
   nameIndex = index of field containing the name of the values being added
   data = output data fields (common followed by datavalues)
   names = string of field names added to common separted by outputSeparator
   Note that the same names should be produced next time.
   input = last line read (becomes the first line of the next common block)
   returns pointer past common context in output.
   input will altered to the null string when EOF read.
*/
{
  while (!input[0]) //read first line if this is first block
    if (!loadLine(in, input)) {  //read first line of next common block
      names[0] = output[0] = '\0';
      return input;
  }
  char *commonEnd = extractCommon(input, output);  //common context fields
  char *outEnd = &output[0] + sizeof(tableLine);
  char *outCursor = addField(input, valueIndex, commonEnd, outEnd);
  char *namesEnd = &names[0] + sizeof(tableLine);
  char *nameCursor = addField(input, nameIndex, &names[0], namesEnd);
  size_t commonLen = commonEnd - output;
  while (loadLine(in, input)) {
    if (input[0]) { //skip blank lines
      tableLine context;
      char *contextEnd = extractCommon(input, context);
      size_t contextLen = contextEnd-context;
      if (commonLen != contextLen || memcmp(context, output, contextLen))
        break;
      outCursor = addField(input, valueIndex, outCursor, outEnd);
      nameCursor = addField(input, nameIndex, nameCursor, namesEnd);
    }
  }
  outCursor[-1] = nameCursor[-1] = '\0';  //remove tailing separators
  return commonEnd;
}


int main(int argc, char **argv)
{
  const static struct option options[] = {
    {"separator", 1, NULL, 's'},  //input separator
    {"outputSeparator", 1, NULL, 'o'},
    {"debug", 2, NULL, 'd'},
    {"help", 0, NULL, 'h'},
    {NULL}
  };

  char *env;;
  if (env = getenv("common"))
    commonEnv = env;
  if (env = getenv("value"))
    valueEnv = env;
  if (env = getenv("extra"))
    extraEnv = env;
  progName = basename(argv[0]);
  for (;;) {
    int optc = getopt_long_only(argc, argv, "", options, 0);
    switch (optc) {
      case -1:
        goto gotAllOpts;
      case 's':  //input separator
        separator=optarg;
        unescape(separator);
        if (separator[1])
          syntaxErr("Column separator must be a single character");
        break;
      case 'o':  //output separator
        outputSeparator=optarg;
        unescape(outputSeparator);
        if (outputSeparator[1])
          syntaxErr("Output separator must be a single character");
        break;
      case 'd':  //display debuging status info
        debug = optarg ? atoi(optarg) : 1;
        break;
      case 'h':
        usage();
        return 0;
      default:
        syntaxErr("invalid option: %s", argv[optind]);
    }
  }
gotAllOpts: ; //require argument specifying column id
  if (debug && optind < argc-1)
    fprintf(stderr, "Ignored excess command options\n");
  char *idField = argv[optind];
  int idFieldNum;
  if (!idField) {
    usage();
    return 2;
  }
  loadLine(stdin, header);
  parseHeader();
  size_t nameIndex = parseField(idField, strlen(idField));
  size_t valueIndex = parseField(valueEnv, strlen(valueEnv));
  parseMap(commonEnv, &commonMap);
  parseMap(extraEnv, &extraMap);

  char *values = nextBlock(
    outLine, initialNames, inLine, stdin, valueIndex, nameIndex);
  putMap(stdout, commonEnv);
  fputs(initialNames, stdout);
  if (extraMap.indices) {  //append any extra, unchanging values to table header
    remap(&extraMap, inLine, extraLine);
    printf("%c%s", *outputSeparator, extraLine);
  }
  puts("");
  for(;;) {
    puts(outLine);
    if (!inLine[0])
      break;
    unsigned startLine = lineno;
    values = nextBlock(outLine, names, inLine, stdin, valueIndex, nameIndex);
    if (strcmp(initialNames, names)) {
      if (debug>3) {
        fprintf(stderr,
        "Table altered format at line #%u:\n[%s] became\n[%s]\n",
                startLine, initialNames, names);
        if (debug>4 && strlen(initialNames)!=strlen(names))
          fprintf(stderr, "length changed!\n");
      }  //try to rearrange the values to conform to the initialNames
      strcpy(extraLine, values);
      char *outEnd = &outLine[0] + sizeof(tableLine);
      const char *initialName = &initialNames[0];
      if (*initialName) {
        do {
          const char *initialNameEnd = fieldEnd(initialName, *outputSeparator);
          size_t initialNameLen = initialNameEnd - initialName;
          ssize_t index = findName(&names[0], initialName, initialNameLen);
          const char *dataValue;
          if (index < 0) {
            if (debug)
              fprintf(stderr, "Missing [%.*s] data in lines %u..%u\n",
                      (int)initialNameLen, initialName, startLine, lineno);
            dataValue = "";
          }else
            dataValue = fieldStart(extraLine, index, *outputSeparator);
          values = addString(dataValue, *outputSeparator, values, outEnd);
          initialName = initialNameEnd + (*initialNameEnd!=0);
        } while (*initialName);
        *--values = '\0';  //delete trailing separator
      }
    }
  }
  return 0;
}
