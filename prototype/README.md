# Documents folder reorganization

This is an effort to reorganize my documents folder. This will double as an archival and exhibition that could someday be made public.

I found that most of my folders represent a project, so there will be one combined projects folder, with other folders containing organized links.

## Spec
**What is a project?**
Anything that will be useful on its own. For example, a school course may have multiple 'projects', but likely they are not useful outside the contect of that course as an overarching 'project'

**Benefits**
- Flexibility (can reorganize projects as much as I want)
- Tagging (projects can belong to multiple folders)
- Consistency (projects will always have the same path, no matter how I decide to organize them)

**Naming convention**
- all lower case with spaces (except as needed): most readable
    - All other cases do not wrap nicely
    - If you intend to import from python, use snake case
    - Windows doesn't respect folder case, avoid if possible
    - No spaces suitable for web resources
    - Kebab case suitable for npm libraries
- Don't rename established folders
- Names should be standalone without the context of their containing folder

`Python` and `web-ext` must stay where they are for legacy purposes, plus I mostly like their organization already.

**What happens to completed/abandoned projects?**
That remains to be decided. However, DON'T zip the folder because
- storage isn't a concern
- more inconvenient to resume or view
- Folders that were once ignored become part of archive

**Potential organization**
I think it makes sense to organize to optimize access speed.
- `done`
- `suspended`
- Infrequent yet evergreen (documentation) projects located in folders
- Active projects


## Tooling
To assist in the migration and maintenance, I need to make a python command line tool

**Backend comparison**
| Feature                                  | Junction | Shortcut |
| ---------------------------------------- | :------: | :------: |
| Easy to create from GUI without CLI tool |     ❌    |     ✅    |
| Syncable (ideally)                       |     ❌    |     *️⃣1     |
| Easy to get to source (for permalinking) |     ❌    |     ✅    |
| Appear in folder selectors               |     ✅    |     ❌    |
| Use breadcrumbs                          |     ✅    |     ❌    |
| View/edit sync status                    |     *️⃣2    |     ✅    |
| Set whole grouping as "always offline"   |     *️⃣3    |     *️⃣3    |

Some notes:
1. Shortcut broken after sync
2. Workaround: show "attributes" column and [learn the codes](https://en.wikipedia.org/wiki/File_attribute)
3. Workaround: additional config file that [sets programmatically](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/attrib)

Shortcuts seem ideal since there's one source of truth

<details>

<summary><h3>Imperitive implementation</h3></summary>

One synced folder containing flattened projects (`_projects`) and shortcuts (`.lnk`) to organize the projects

Since Windows shortcuts require full paths, the user will need to configure a `%PROJECTS_ROOT%` environment variable so links work across (Windows) computers. The tooling will help make shortcuts that follow this convention.

**Actions**
- `convert`: Treat all the folders in cwd as projects. Move them to `_projects` path (as defined by system env) and replace with shortcuts
- `find`: Traverse the folder above `%PROJECTS_ROOT%` and find all locations where the cwd project is used (useful for deduplication or reorganization)
- `rename`: do find, then fix all shortcuts to point to the new location.

**Challenges**
- shortcut .lnk files do not work when synced across computers
- directory junctions or symlinks are treated as duplicates (link lost when syncing)
- TODO: why doesn't `node_modules` sync?

</details>

### Declarative Implementation
A `projects.json` file in `%PROJECTS_ROOT%` that stores a mapping of project name to `["path/to/dir", "route/to/dir", ...]`. The cli then reconsiles or saves the declared state with the actual state using directory junctions. The backend could be adapted to support shortcuts as well.

**env**
Needed for script to know where to place/read files
- `%PROJECTS_ROOT%`: location containing flat list of all projects (can be synced)
- `%DOCS_VIEW_ROOT%`: location where `projects.json` will be expanded (mustn't be synced)

**CLI commands**
- `save`: Traverse `%DOCS_VIEW_ROOT%` and update `projects.json`
- `load`: Create `%DOCS_VIEW_ROOT%` from `projects.json`
- `link <project?>`
    1. prompt user for project (providing autocomplete suggestions)
    2. create entry in `projects.json` for that project to the cwd
    3. `load`
- `link-to <path>`
	1. Create entry in `projects.json` for cwd folder name project to `<path>`
	2. `load`
- `convert *`:
	1. Treat every folder in the cwd as a project
	2. move it to `PROJECTS_ROOT`
	3. update `projects.json` to reflect the old structure
	4. `load`
- `convert <project>`: start from step 2 of `convert *` only for the specified project
	