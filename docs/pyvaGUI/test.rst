test module
===========

Das manuell ausführbare Testskript lädt oder erstellt ``bibliothek.json``, gibt
die enthaltenen Materialnamen aus und ergänzt ein äquivalentes Fluid.

.. note::

   Das Modul wird hier nicht mit ``automodule`` importiert, weil sein Import die
   Bibliotheksdatei verändert. Die getesteten APIs sind unter
   :mod:`core.library` und :mod:`core.materials` dokumentiert.
