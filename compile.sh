#!/bin/bash

cd $1

export PATH=$2/bin:$PATH
export LD_LIBRARY_PATH=$2/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

DreamMaker test.dme
DreamDaemon test.dmb -close -verbose -ultrasafe | cat
