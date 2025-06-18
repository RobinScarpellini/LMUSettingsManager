# LMU Configuration Editor - Development Context

## Project Background

### The Problem Space

Le Mans Ultimate (LMU) is a sophisticated racing simulation that stores its configuration in two separate files with different formats and structures. The game's `settings.json` file uses a non-standard JSON format with embedded comments containing field descriptions, while `Config_DX11.ini` handles graphics settings in traditional INI format.

Currently, players must:
- Manually edit text files to access advanced settings
- Risk breaking JSON syntax when making changes
- Manage multiple configurations by copying and renaming files
- Remember which settings do what without built-in documentation
- Switch between configurations by manually swapping files

This creates a significant barrier for players who want to optimize their experience for different racing conditions, share setups with teammates, or simply access the full range of available options.

### User Research Insights

Through community feedback and forum analysis, we've identified several key user groups:

1. **Competitive Racers**: Need different configurations for practice, qualifying, and race sessions. Often maintain separate setups for different weather conditions.

2. **League Organizers**: Require standardized settings across all participants. Need to distribute and verify configuration compliance.

3. **Content Creators**: Frequently switch between high-quality settings for recordings and performance settings for streaming.

4. **Casual Players**: Want easier access to settings without editing text files. Often unaware of available options.

### Design Philosophy

The editor follows these core principles:

1. **Preserve, Don't Transform**: The tool must maintain the exact structure and formatting of the original files, including comments and field ordering.

2. **Zero Validation**: Users should be able to enter any value they want. The tool trusts users to know what they're doing or learn from their mistakes.

3. **Descriptive Guidance**: Every setting displays its original comment/description to help users understand its purpose.

4. **Fast Workflow**: Common tasks (switching configs, applying changes) should require minimal clicks.

5. **Safe Experimentation**: Users can always revert changes or load known-good configurations.

## Technical Context

### File Format Challenges

#### settings.json Structure
```json
{
  "CATEGORY": {
    "Setting Name": value,  // Description text #: "This is what the setting does"
    "Another Setting": value
  }
}
```

The non-standard comment format requires custom parsing:
- Comments use `//` but are not valid JSON
- Descriptions follow `#:` marker within comments
- Field order must be preserved (not guaranteed by standard JSON parsers)
- Some values are arrays or nested objects

#### Config_DX11.ini Structure
```ini
[SECTION]
Key=Value
AnotherKey=123
// Comments can appear anywhere
```

INI considerations:
- Comments use `//` prefix
- Some values contain special characters
- Sections must maintain order
- Boolean values use various formats (0/1, true/false)

### Configuration Storage Pattern

LMU uses a specific naming convention for saved configurations:
- `conf_<name>_settings.json`
- `conf_<name>_Config_DX11.ini`

These files must:
- Exist in pairs (both files for each configuration)
- Use identical `<name>` portion
- Reside in the same directory as active configs

### Steam Integration

The game is primarily distributed through Steam, requiring registry access to locate installations:

1. Check `HKEY_LOCAL_MACHINE\SOFTWARE\Valve\Steam` (32-bit)
2. Check `HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Valve\Steam` (64-bit)
3. Parse `steamapps/libraryfolders.vdf` for game libraries
4. Search each library for `Le Mans Ultimate` folder

### File Access Considerations

Common issues that must be handled:
- Game running locks configuration files
- Steam cloud sync may delay file availability
- Antivirus software may block file writes
- Users may lack write permissions

## Design Decisions and Rationale

### Why No Field Validation?

The decision to skip validation is deliberate:
1. **Future-Proofing**: Game updates may add new valid values
2. **Advanced Users**: Power users may use undocumented values
3. **Experimentation**: Users should be free to test settings
4. **Simplicity**: Reduces maintenance burden
5. **Trust**: Respects user expertise

### Why Preserve File Structure?

Maintaining exact file structure is critical:
1. **Game Compatibility**: Ensures files remain valid
2. **Comment Preservation**: Keeps helpful descriptions
3. **Diff-Friendly**: Makes it easy to see what changed
4. **User Confidence**: Files look familiar when manually inspected
5. **Rollback Safety**: Can always return to original state

### UI/UX Design Rationale

#### Tab Organization
Categories mirror the game's internal organization, making it intuitive for users familiar with the game files.

#### Right-Side Configuration Panel
Keeps configuration management always visible, reinforcing the multi-config nature of the tool.

#### Search at Top
Follows standard application patterns, making discovery immediate and obvious.

#### Field Descriptions
Shows descriptions inline rather than as tooltips to ensure users see them without interaction.

## Implementation Considerations

### Performance Optimizations

With hundreds of settings across multiple categories, performance is critical:

1. **Lazy Loading**: Only render visible widgets
2. **Search Indexing**: Pre-build search index on startup
3. **Debounced Input**: Prevent excessive updates during typing
4. **Virtual Scrolling**: Recycle widgets for long lists
5. **Background Operations**: File I/O in separate thread

### Error Handling Philosophy

Errors should be:
1. **User-Friendly**: No technical jargon or stack traces
2. **Actionable**: Tell users how to fix the problem
3. **Contextual**: Different messages for different scenarios
4. **Recoverable**: Offer retry options where possible
5. **Logged**: Keep technical details for support

### Change Tracking Strategy

The application tracks changes at multiple levels:
1. **Field Level**: Each widget knows its original value
2. **Model Level**: Central tracking of all modifications
3. **Visual Level**: Modified fields show indicators
4. **Action Level**: Apply button shows change count

### File Writing Safety

To prevent data loss:
1. **Backup First**: Create .bak files before writing
2. **Atomic Writes**: Write to temp file, then rename
3. **Validation**: Verify written content matches expected
4. **Rollback**: Restore from backup on failure


## Technical Challenges and Solutions

### Challenge: Parsing JSON with Comments

**Solution**: Line-by-line parsing that:
- Extracts comments before JSON parsing
- Maps comments to fields by line association
- Rebuilds file preserving original structure

### Challenge: Maintaining Field Order

**Solution**: Use OrderedDict throughout:
- Parse with object_pairs_hook
- Store in ordered structures
- Write in original sequence

### Challenge: Large Number of Fields

**Solution**: Multi-pronged approach:
- Lazy loading of tab content
- Virtual scrolling for long lists
- Search to quickly find fields
- Keyboard navigation shortcuts

### Challenge: File Locking by Game

**Solution**: Intelligent error handling:
- Detect specific Windows error codes
- Provide clear user message
- Offer retry after game closes
- No silent failures

### Challenge: Different Boolean Representations

**Solution**: Unified handling:
- Detect various formats (0/1, true/false, on/off)
- Present as consistent toggle switches
- Write back in original format

## Future Considerations

### Potential Features

1. **Profile Management**: User profiles with multiple configuration sets
2. **Cloud Sync**: Backup configurations to cloud storage
3. **Preset Library**: Community-shared configuration presets
4. **Diff View**: Visual diff between configurations
5. **Batch Operations**: Apply same change across multiple configs
6. **Undo/Redo**: Full undo stack for changes
7. **Themes**: Dark mode and custom themes
8. **Localization**: Multi-language support


## Development Best Practices

### Code Organization

- **Separation of Concerns**: Clear boundaries between UI, business logic, and file operations
- **Dependency Injection**: Pass dependencies explicitly
- **Interface Segregation**: Small, focused interfaces
- **Single Responsibility**: Each class has one clear purpose

### Documentation Requirements
- **Code Comments**: Explain why, not what
- **Docstrings**: Google style for all public methods
- **README**: Clear setup and usage instructions

## Conclusion

The LMU Configuration Editor fills a clear need in the sim racing community by providing safe, easy access to game settings. By focusing on user needs, maintaining file integrity, and providing a polished experience, this tool can become an essential companion application for Le Mans Ultimate players.

The technical approach prioritizes reliability and user trust while providing powerful features for advanced users. Through careful implementation of the phases outlined in the JSON specification and adherence to the principles in this context document, the development team can create a tool that enhances the LMU experience for all player types