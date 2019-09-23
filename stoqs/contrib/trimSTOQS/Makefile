CFLAGS=-O2
DEBUG_CFLAGS=-O0 -g
CC=gcc

trimSTOQS:  trimSTOQS.c
	$(CC) -o $@ $(CFLAGS) $<

debug:  trimSTOQS.c
	$(CC) -o trimSTOQS $(DEBUG_CFLAGS) $<

clean:
	rm -f trimSTOQS
