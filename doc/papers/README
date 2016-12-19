papers directory
----------------

To build PDFs of the papers in the subdirectories you'll need LaTeX and IEEETrans.

Install with:

    sudo yum install texlive texlive-placeins texlive-upquote
    cd ~/Downloads
    wget http://mirrors.ctan.org/macros/latex/contrib/IEEEtran.zip
    unzip IEEEtran.zip

Locate where texlive got installed on your system and install extras there, e.g.:

    export TEXLIVE_HOME=/usr/share/texlive/texmf-dist
    cd $TEXLIVE_HOME/tex/latex
    sudo unzip ~/Downloads/IEEEtran.zip 
    cd $TEXLIVE_HOME/bibtex/bst
    sudo cp -r $TEXLIVE_HOME/tex/latex/IEEEtran/bibtex/*.bst .
    sudo texhash

In the paper's directory build the bibliography and the paper:

    cd OINA2017
    export BIBINPUTS=$TEXLIVE_HOME/tex/latex/IEEEtran/bibtex
    export BSTINPUTS=$TEXLIVE_HOME/tex/latex/IEEEtran/bibtex
    rm *.aux
    pdflatex VisualizingDatawithSTOQS.tex 
    bibtex VisualizingDatawithSTOQS.bib && pdflatex VisualizingDatawithSTOQS.tex
   
Examine the resulting .pdf file using gs(1) on your VM, or copy it to /vagrant and
view it with your host OS's PDF viewer. For quick cycles on editing execute this
command and leave the MacOS Preview app opened on the file ~/Downloads/VisualizingDatawithSTOQS.pdf:

    pdflatex VisualizingDatawithSTOQS.tex && bibtex VisualizingDatawithSTOQS.bib && pdflatex VisualizingDatawithSTOQS.tex && cp VisualizingDatawithSTOQS.pdf /mnt/hgfs/<user>/Downloads

If errors happen in the latex processing you may need to `rm *.aux` to clear them up.

 
