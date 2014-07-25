PLUGIN = collectd_sensu.py
PLUGIN_DIR = lib
VERSION := $(shell cat $(PLUGIN_DIR)/$(PLUGIN) | egrep ^'VERSION =' | cut -d ' ' -f 3 | cut -d \" -f 2)
DEST_DIR = /opt/collectd-sensu-$(VERSION)

install:
	@mkdir -p $(DEST_DIR)/$(PLUGIN_DIR)
	@cp $(PLUGIN_DIR)/$(PLUGIN) $(DEST_DIR)/$(PLUGIN_DIR)
	@echo "Installed collected_sensu plugin, add this"
	@echo "to your collectd configuration to load this plugin:"
	@echo
	@echo '    <LoadPlugin "python">'
	@echo '        Globals true'
	@echo '    </LoadPlugin>'
	@echo
	@echo '    <Plugin "python">'
	@echo '        # $(PLUGIN) is at $(DEST_DIR)/$(PLUGIN_DIR)/$(PLUGIN)'
	@echo '        ModulePath "$(DEST_DIR)/$(PLUGIN_DIR)"'
	@echo '        Interactive false'
	@echo
	@echo '        Import "collectd_sensu"'
	@echo
	@echo '    </Plugin>'
