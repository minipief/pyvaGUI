pyvaGUI module
==============

Das Modul ist der ausführbare Einstiegspunkt der Anwendung. Es erzeugt eine
``QApplication``, zeigt :class:`gui.main_window.MainWindow` an und startet die
Qt-Ereignisschleife.

.. note::

   Das Modul wird hier nicht mit ``automodule`` importiert, da bereits der
   Import die grafische Anwendung startet und den Sphinx-Build blockieren würde.
