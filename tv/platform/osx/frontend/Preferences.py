from objc import YES, NO, nil
from AppKit import *
from Foundation import *
from PyObjCTools import NibClassBuilder

import app
import feed
import prefs
import views
import config
import dialogs
import eventloop
import platformutils

from gtcache import gettext as _

NibClassBuilder.extractClasses(u"PreferencesWindow")

###############################################################################

class PreferenceItem (NSToolbarItem):

    def setView_(self, view):
        self.view = view

###############################################################################

class PreferencesWindowController (NibClassBuilder.AutoBaseClass):

    def init(self):
        super(PreferencesWindowController, self).initWithWindowNibName_("PreferencesWindow")
        return self

    def awakeFromNib(self):
        self.items = dict()
        self.allIdentifiers = list()
        
        generalItem = self.makePreferenceItem(u"GeneralItem", _(u"General"), u"general_pref", self.generalView)
        channelsItem = self.makePreferenceItem(u"ChannelsItem", _(u"Channels"), u"channels_pref", self.channelsView)
        downloadsItem = self.makePreferenceItem(u"DownloadsItem", _(u"Downloads"), u"downloads_pref", self.downloadsView)
        downloadsItem = self.makePreferenceItem(u"FoldersItem", _(u"Folders"), u"folders_pref", self.foldersView)
        diskSpaceItem = self.makePreferenceItem(u"DiskSpaceItem", _(u"Disk Space"), u"disk_space_pref", self.diskSpaceView)
        playbackItem = self.makePreferenceItem(u"PlaybackItem", _(u"Playback"), u"playback_pref", self.playbackView)

        initialItem = generalItem

        toolbar = NSToolbar.alloc().initWithIdentifier_(u"Preferences")
        toolbar.setDelegate_(self)
        toolbar.setAllowsUserCustomization_(NO)
        toolbar.setSelectedItemIdentifier_(initialItem.itemIdentifier())

        self.window().setToolbar_(toolbar)
        if hasattr(self.window(), 'setShowsToolbarButton_'): # 10.4 only
            self.window().setShowsToolbarButton_(NO)
        self.switchPreferenceView_(initialItem)

    def makePreferenceItem(self, identifier, label, imageName, view):
        item = PreferenceItem.alloc().initWithItemIdentifier_(identifier)
        item.setLabel_(label)
        item.setImage_(NSImage.imageNamed_(imageName))
        item.setTarget_(self)
        item.setAction_("switchPreferenceView:")
        item.setView_(view)
        
        identifier = item.itemIdentifier()
        self.items[identifier] = item
        self.allIdentifiers.append(identifier)
        
        return item

    def windowWillClose_(self, notification):
        self.window().endEditingFor_(nil)
        config.save()

    def toolbarAllowedItemIdentifiers_(self, toolbar):
        return self.allIdentifiers

    def toolbarDefaultItemIdentifiers_(self, toolbar):
        return self.allIdentifiers

    def toolbarSelectableItemIdentifiers_(self, toolbar):
        return self.allIdentifiers

    def toolbar_itemForItemIdentifier_willBeInsertedIntoToolbar_(self, toolbar, itemIdentifier, flag ):
        return self.items[ itemIdentifier ]

    def validateToolbarItem_(self, item):
        return YES

    def switchPreferenceView_(self, sender):
        if self.window().contentView() == sender.view:
            return

        window = self.window()
        wframe = window.frame()
        vframe = sender.view.frame()
        toolbarHeight = wframe.size.height - window.contentView().frame().size.height
        wframe.origin.y += wframe.size.height - vframe.size.height - toolbarHeight
        wframe.size = vframe.size
        wframe.size.height += toolbarHeight

        self.window().setContentView_(sender.view)
        self.window().setFrame_display_animate_(wframe, YES, YES)

###############################################################################

class GeneralPrefsController (NibClassBuilder.AutoBaseClass):
    
    def awakeFromNib(self):
        run = config.get(prefs.RUN_DTV_AT_STARTUP)
        self.runAtStartupCheckBox.setState_(run and NSOnState or NSOffState)
    
    def runAtStartup_(self, sender):
        run = (sender.state() == NSOnState)
        app.delegate.makeAppRunAtStartup(run)
        config.set(prefs.RUN_DTV_AT_STARTUP, run)
                    
###############################################################################

class ChannelsPrefsController (NibClassBuilder.AutoBaseClass):

    def awakeFromNib(self):
        minutes = config.get(prefs.CHECK_CHANNELS_EVERY_X_MN)
        itemIndex = self.periodicityPopup.indexOfItemWithTag_(minutes)
        self.periodicityPopup.selectItemAtIndex_(itemIndex)

    def checkEvery_(self, sender):
        minutes = sender.selectedItem().tag()
        eventloop.addUrgentCall(lambda:config.set(prefs.CHECK_CHANNELS_EVERY_X_MN, minutes), "Setting update frequency pref.")

###############################################################################

class DownloadsPrefsController (NibClassBuilder.AutoBaseClass):
    
    def awakeFromNib(self):
        moviesDirPath = config.get(prefs.MOVIES_DIRECTORY)
        self.moviesDirectoryField.setStringValue_(unicode(moviesDirPath))
        limit = config.get(prefs.LIMIT_UPSTREAM)
        self.limitUpstreamCheckBox.setState_(limit and NSOnState or NSOffState)
        self.limitValueField.setEnabled_(limit)
        self.limitValueField.setIntValue_(config.get(prefs.UPSTREAM_LIMIT_IN_KBS))
        self.maxDownloadsField.setIntValue_(config.get(prefs.MAX_MANUAL_DOWNLOADS))
        btMinPort = config.get(prefs.BT_MIN_PORT)
        self.btMinPortField.setIntValue_(btMinPort)
        btMaxPort = config.get(prefs.BT_MAX_PORT)
        self.btMaxPortField.setIntValue_(btMaxPort)
    
    def limitUpstream_(self, sender):
        limit = (sender.state() == NSOnState)
        self.limitValueField.setEnabled_(limit)
        config.set(prefs.LIMIT_UPSTREAM, limit)
        self.setUpstreamLimit_(self.limitValueField)
    
    def setUpstreamLimit_(self, sender):
        limit = sender.intValue()
        config.set(prefs.UPSTREAM_LIMIT_IN_KBS, limit)
        
    def changeMoviesDirectory_(self):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(NO)
        panel.setCanChooseDirectories_(YES)
        panel.setCanCreateDirectories_(YES)
        panel.setAllowsMultipleSelection_(NO)
        panel.setTitle_(_(u'Movies Directory'))
        panel.setMessage_(_(u'Select a Directory to store %s downloads in.') % config.get(prefs.SHORT_APP_NAME))
        panel.setPrompt_(_(u'Select'))
        
        oldMoviesDirectory = self.moviesDirectoryField.stringValue()
        result = panel.runModalForDirectory_file_(oldMoviesDirectory, nil)
        
        if result == NSOKButton:
            newMoviesDirectory = unicode(panel.directory())
            if newMoviesDirectory != oldMoviesDirectory:
                self.moviesDirectoryField.setStringValue_(newMoviesDirectory)
                summary = _(u'Migrate existing movies?')
                message = _(u'You\'ve selected a new folder to download movies to.  Should %s migrate your existing downloads there?  (Currently dowloading movies will not be moved until they finish).' % config.get(prefs.SHORT_APP_NAME))
                def migrationCallback(dialog):
                    migrate = (dialog.choice == dialogs.BUTTON_YES)
                    app.changeMoviesDirectory(platformutils.osFilenameToFilenameType(newMoviesDirectory), migrate)
                dlog = dialogs.ChoiceDialog(summary, message, dialogs.BUTTON_YES, dialogs.BUTTON_NO)
                dlog.run(migrationCallback)
    
    def setMaxDownloads_(self, sender):
        maxDownloads = self.maxDownloadsField.intValue()
        config.set(prefs.MAX_MANUAL_DOWNLOADS, maxDownloads)

    def setBTMinPort_(self, sender):
        self.validateBTPortValues()
    
    def setBTMaxPort_(self, sender):
        self.validateBTPortValues()

    def validateBTPortValues(self):
        btMinPort = self.btMinPortField.intValue()
        btMaxPort = self.btMaxPortField.intValue()
        if btMinPort > btMaxPort:
            btMaxPort = btMinPort
            self.btMaxPortField.setIntValue_(btMaxPort)
        config.set(prefs.BT_MIN_PORT, btMinPort)
        config.set(prefs.BT_MAX_PORT, btMaxPort)

###############################################################################

class FoldersPrefsController (NibClassBuilder.AutoBaseClass):
    
    def init(self):
        self.folders = list()
        return self
    
    def awakeFromNib(self):
        eventloop.addIdle(self.loadInitialData, 'Adding watched folders initial data')

    def loadInitialData(self):
        for f in views.feeds:
            if isinstance(f.actualFeed, feed.DirectoryWatchFeedImpl):
                self.folders.append(f)
        views.feeds.addAddCallback(self.folderWasAdded)
        views.feeds.addRemoveCallback(self.folderWasRemoved)
        views.feeds.addChangeCallback(self.folderWasChanged)
        self.foldersTable.reloadData()
        
    def addFolder_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(NO)
        panel.setCanChooseDirectories_(YES)
        panel.setCanCreateDirectories_(YES)
        panel.setAllowsMultipleSelection_(NO)
        panel.setTitle_(_(u'View this Directory in My Collection'))
        panel.setMessage_(_(u'Select a Directory to view in My Collection.'))
        panel.setPrompt_(_(u'Select'))
        
        result = panel.runModalForDirectory_file_(nil, nil)
        
        if result == NSOKButton:
            path = platformutils.osFilenameToFilenameType(panel.directory())
            eventloop.addIdle(lambda:self.addFolder(path), 'Adding new watched folder')

    def addFolder(self, path):
        feed.Feed(u'dtv:directoryfeed:%s' % platformutils.makeURLSafe(path))

    def folderWasAdded(self, mapped, id):
        self.folders.append(mapped)
        self.foldersTable.reloadData()

    def removeFolder_(self, sender):
        eventloop.addIdle(self.removeFolders, 'Removing watched folder(s)')

    def removeFolders(self):
        feeds = list()
        for i in range(0, len(self.folders)):
            if self.foldersTable.selectedRowIndexes().containsIndex_(i):
                feeds.append(self.folders[i])
        app.controller.removeFeeds(feeds)

    def folderWasRemoved(self, mapped, id):
        if mapped in self.folders:
            self.folders.remove(mapped)
        self.foldersTable.reloadData()

    def showFolderAsChannel_(self, sender):
        folder = self.folders[sender.selectedRow()]
        eventloop.addIdle(lambda:self.toggleFeed(folder), 'Toggling feed visibility')
    
    def toggleFeed(self, folder):
        folder.setVisible(not folder.visible)
        
    def folderWasChanged(self, mapped, id):
        self.foldersTable.reloadData()
    
    def numberOfRowsInTableView_(self, tableView):
        return len(self.folders)
        
    def tableView_objectValueForTableColumn_row_(self, tableView, col, row):
        if not isinstance(self.folders[row].actualFeed, feed.DirectoryWatchFeedImpl):
            # This feed has apparently not been fully created yet, schedule a refresh...
            self.foldersTable.reloadData()
        else:
            if col.identifier() == 'location':
                return platformutils.filenameTypeToOSFilename(self.folders[row].dir)
            elif col.identifier() == 'asChannel':
                return self.folders[row].visible
        return ''
        
    def tableViewSelectionDidChange_(self, notification):
        self.deleteButton.setEnabled_(self.foldersTable.numberOfSelectedRows() > 0)
            
###############################################################################

class DiskSpacePrefsController (NibClassBuilder.AutoBaseClass):
    
    def awakeFromNib(self):
        preserve = config.get(prefs.PRESERVE_DISK_SPACE)
        self.preserveSpaceCheckBox.setState_(preserve and NSOnState or NSOffState)
        self.minimumSpaceField.setEnabled_(preserve)
        self.minimumSpaceField.setFloatValue_(config.get(prefs.PRESERVE_X_GB_FREE))
        itemTag = int(config.get(prefs.EXPIRE_AFTER_X_DAYS) * 24)
        itemIndex = self.expirationDelayPopupButton.indexOfItemWithTag_(itemTag)
        self.expirationDelayPopupButton.selectItemAtIndex_(itemIndex)
    
    def preserveDiskSpace_(self, sender):
        preserve = (sender.state() == NSOnState)
        self.minimumSpaceField.setEnabled_(preserve)
        config.set(prefs.PRESERVE_DISK_SPACE, preserve)
        self.setMinimumSpace_(self.minimumSpaceField)
    
    def setMinimumSpace_(self, sender):
        space = sender.floatValue()
        config.set(prefs.PRESERVE_X_GB_FREE, space)
        
    def setExpirationDelay_(self, sender):
        delay = sender.selectedItem().tag()
        config.set(prefs.EXPIRE_AFTER_X_DAYS, delay / 24.0)

###############################################################################

class PlaybackPrefsController (NibClassBuilder.AutoBaseClass):

    def awakeFromNib(self):
        remember = config.get(prefs.RESUME_VIDEOS_MODE)
        self.rememberCheckBox.setState_(remember and NSOnState or NSOffState)
        singleMode = config.get(prefs.SINGLE_VIDEO_PLAYBACK_MODE)
        self.modesMatrix.selectCellWithTag_(int(singleMode))

    def rememberVideoPosition_(self, sender):
        remember = (sender.state() == NSOnState)
        config.set(prefs.RESUME_VIDEOS_MODE, remember)

    def setPlaybackMode_(self, sender):
        singleMode = bool(sender.selectedCell().tag())
        config.set(prefs.SINGLE_VIDEO_PLAYBACK_MODE, singleMode)

###############################################################################
