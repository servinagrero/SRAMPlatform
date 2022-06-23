Deployment
==========

Once all the software is installed and the hardware is properly connected, the station should be ready for deployment.
The deployment of the station can be carried out with the use of systemd services.


.. code-block:: text

  [Unit]
  Description=SRAM Reliability Platform
  After=network.target

  [Service]
  Type=simple
  Restart=always
  RestartSec=5
  WorkingDirectory=/path/to/SRAMPlatform
  ExecStart=/path/to/virtualenv/bin/python3 main.py

  [Install]
  WantedBy=multi-user.target



Operations can be scheduled by using the send_command.py script provided and a systemd timer (very similar to a cron job). The following example illustrates how to create the files necesary to power off the platform every friday at 17:00.

.. code-block:: text

  [Unit]
  Description=Power off the SRAM Platform

  [Timer]
  OnCalendar=Fri *-*-* 17:00:00
  Persistent=true

  [Install]
  WantedBy=timers.target


.. code-block:: text

  [Unit]
  Description=Power off the SRAM Platform
  After=network.target

  [Service]
  Type=oneshot
  RemainAfterExit=true
  WorkingDirectory=/path/to/SRAMPlatform
  ExecStart=/path/to/virtualenv/bin/python3 send_command.py "OFF"

  [Install]
  WantedBy=multi-user.target
