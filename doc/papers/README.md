papers directory
----------------

To build PDFs of the papers in the subdirectories you'll need LaTeX and IEEEtran. 
Starting with a standard STOQS installation, install with:

```bash
sudo yum -y install texlive texlive-placeins texlive-upquote
cd ~/Downloads
wget http://mirrors.ctan.org/macros/latex/contrib/IEEEtran.zip
```

Locate where texlive got installed on your system, set the `TEXLIVE_HOME` environment
variable to that directory, and finish the IEEEtran install, e.g.:

```bash
export TEXLIVE_HOME=/usr/share/texlive/texmf-dist
cd $TEXLIVE_HOME/tex/latex
sudo unzip ~/Downloads/IEEEtran.zip 
cd $TEXLIVE_HOME/bibtex/bst
sudo cp -r $TEXLIVE_HOME/tex/latex/IEEEtran/bibtex/*.bst .
sudo texhash
```

In the paper's directory build the bibliography and the paper, e.g.:

```bash
cd ~/dev/stoqsgit/doc/papers/OINA2017
export BIBINPUTS=$TEXLIVE_HOME/tex/latex/IEEEtran/bibtex
export BSTINPUTS=$TEXLIVE_HOME/tex/latex/IEEEtran/bibtex
pdflatex VisualizingDatawithSTOQS.tex 
bibtex VisualizingDatawithSTOQS && pdflatex VisualizingDatawithSTOQS.tex
```
   
Examine the resulting .pdf file using gs(1) on Linux, or copy it to /vagrant and
view it with your host OS's PDF viewer. For quick cycles on editing execute this
command and leave the MacOS Preview app (or other PDF viewer) opened on the file 
~/Vagrants/stoqsvm/VisualizingDatawithSTOQS.pdf:

    pdflatex VisualizingDatawithSTOQS.tex && bibtex VisualizingDatawithSTOQS && pdflatex VisualizingDatawithSTOQS.tex && cp VisualizingDatawithSTOQS.pdf /vagrant

If errors happen in the latex processing you may need to `rm *.aux` to clear them up.

