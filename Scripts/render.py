from jinja2 import Environment, FileSystemLoader
import os
import shutil 
import argparse, sys, json

tmp_dir = '.tmp'
aws_cpp_source = "H:/work/aws-sdk/aws-sdk-cpp"
output_dir = 'Output'


def deletetempdirectory():
    shutil.rmtree(os.path.join(".", tmp_dir))

def createtempdirectory():
    if os.path.isdir(os.path.join(".", tmp_dir)):
        print("Deleting old temp working directory")
        deletetempdirectory()
    
    os.mkdir(os.path.join(".", tmp_dir))


def makeSkeletonFolderStruct(context):
    plugin_name = context['plugin-name']
   

    #Plugin paths
    plugin_path = os.path.join(".", tmp_dir, plugin_name)
    plugin_source_path = os.path.join(plugin_path, "Source")
    
    #Plugin Folders
    os.mkdir(plugin_path)
    os.mkdir(plugin_source_path)
    os.mkdir(os.path.join(plugin_path, "Resources"))

    #Make ThirdParty Folder
    os.mkdir(os.path.join(plugin_source_path, "ThirdParty"))

    for mod in context['client-modules']:
        #Client Module Folders
        os.mkdir(os.path.join(plugin_source_path, f"{mod['client-module-name']}"))
        os.mkdir(os.path.join(plugin_source_path, f"{mod['client-module-name']}", "Private"))
        os.mkdir(os.path.join(plugin_source_path, f"{mod['client-module-name']}", "Public"))

        for tp in mod['TPModules']:
            #Third Party Module Folder
            tp_module_name = tp['TPModuleName']
            tp_path = os.path.join(plugin_source_path, "ThirdParty", tp_module_name )
           
            if os.path.isdir(tp_path):
                continue

            os.mkdir(tp_path)
            
            for platform in context['supported_platforms']:
                os.mkdir(os.path.join(tp_path, platform['Platform']))
    
                for SubPlatform in platform['Sub-Platforms']:
                    os.mkdir(os.path.join(tp_path, platform['Platform'], SubPlatform))
    

def copyFilesFromBuild(context):
    #We need to copy the binary and header files of the actual aws sdk into the TP module folders
    plugin_name = context['plugin-name']

    #Plugin paths
    plugin_path = os.path.join(".", tmp_dir, plugin_name)
    plugin_source_path = os.path.join(plugin_path, "Source")

    #for each client module look at the needed tp dependencies
    for clientmodule in context['client-modules']:
        for tpmodule in clientmodule['TPModules']:
            tp_path = os.path.join(plugin_source_path, "ThirdParty", tpmodule['TPModuleName'])
            isdirEmpty = True
            for dirpath, dirnames, files in os.walk(tp_path):
                if files:
                    #if we walk this folder we should not find any files unless we have already made this TP Module already 
                    isdirEmpty = False
                    break

            if not isdirEmpty:
                print(f"You have already made a {tpmodule['TPModuleName']} so you do not need two copies") 
                continue

            #Header files from source code
            header_src = os.path.join( context['binaries-path'], tpmodule['aws-sdk-name'], "aws")
            header_dst = os.path.join(tp_path, "aws")
            print(f"copying folder {header_src} to {header_dst}")
            shutil.copytree(header_src, header_dst)

            #Platform binaries
            #For each platform type copy the binaries
            for platform in context['supported_platforms']:
                platform_dir = os.path.join(tp_path, platform['Platform'])

                if len(platform['Sub-Platforms']) != 0:
                    for SubPlatform in platform['Sub-Platforms']:
                        sub_plat_dir = os.path.join(platform_dir, SubPlatform)
                        for filetype in platform['File-Types']:
                            filename = filetype['file-name'](tpmodule['aws-sdk-name'])

                            #make src file location
                            src = os.path.join(context['binaries-path'], tpmodule['aws-sdk-name'], filename)
                            dst = os.path.join(sub_plat_dir, filename )

                            print(f"Copying {src} to {dst}")
                            shutil.copyfile(src, dst)
                else:
                    for filetype in platform['File-Types']:
                        filename = filetype['file-name'](tpmodule['aws-sdk-name'])

                        #make src file location
                        src = os.path.join(context['binaries-path'], tpmodule['aws-sdk-name'], filename)
                        dst = os.path.join(platform_dir, filename)

                        print(f"Copying {src} to {dst}")
                        shutil.copyfile(src, dst)


def genetateTPTemplates(context):
    #We need to generate the template files for the third party modules
    plugin_name = context['plugin-name']

    #Plugin paths
    plugin_path = os.path.join(".", tmp_dir, plugin_name)
    plugin_source_path = os.path.join(plugin_path, "Source")

    #jinja env
    env = Environment(loader=FileSystemLoader('templates'))

    #for each client module look at the needed tp dependencies
    for clientmodule in context['client-modules']:
        for tpmodule in clientmodule['TPModules']:
            tp_path = os.path.join(plugin_source_path, "ThirdParty", tpmodule['TPModuleName'])

            for template in context['tp-templates']:
                template_dst = template['path'](tp_path, tpmodule)
                
                if os.path.isfile(template_dst):
                    print(f"We have already made the generate files for the {tpmodule['TPModuleName']}")
                    break
                
                jinja_temp = env.get_template(template['name'])
                output = jinja_temp.render(context=tpmodule)
                print(template['msg'](tpmodule))

                with open(template_dst, 'w') as fh:
                    fh.write(output)
                

def makeTPModules(context):
    copyFilesFromBuild(context)

    genetateTPTemplates(context)

def generateClientTemplates(context):
    #We need to generate the template files for the third party modules
    plugin_name = context['plugin-name']

    #Plugin paths
    plugin_path = os.path.join(".", tmp_dir, plugin_name)
    plugin_source_path = os.path.join(plugin_path, "Source")

    #jinja env
    env = Environment(loader=FileSystemLoader('templates'))
    
    for client_mod in context['client-modules']:
        client_path = os.path.join(plugin_source_path, client_mod['client-module-name'])

        #the module needs to know this to do some file finding 
        client_mod['plugin-name'] = context['plugin-name']
        
        for template in context['client-templates']:
            temp_dst = os.path.join(client_path, template['path'](client_mod['client-module-name']))

            jinja_temp = env.get_template(template['name'])
            output = jinja_temp.render(client_context=client_mod)

            print(template['msg'](client_mod['client-module-name']))
            with open(temp_dst,'w') as fh:
                fh.write(output)

def generatePlugingTemplates(context):
    #We need to generate the template files for the third party modules
    plugin_name = context['plugin-name']

    #Plugin paths
    plugin_path = os.path.join(".", tmp_dir, plugin_name)

    #jinja env
    env = Environment(loader=FileSystemLoader('templates'))

    for plugin_temp in context['plugin-templates']:
        plugin_dst = os.path.join(plugin_path, plugin_temp['path'](context['plugin-name']))

        jinja_temp = env.get_template(plugin_temp['name'])
        output = jinja_temp.render(context=context)

        print(plugin_temp['msg'](context['plugin-name']) )
        with open(plugin_dst, "w") as fh:
            fh.write(output)

def moveBaseFiles(context):
    plugin_name = context['plugin-name']

    #Plugin paths
    plugin_path = os.path.join(".", tmp_dir, plugin_name)

    baseTPModule_src = os.path.join('./BaseModules', 'BaseTPLibrary')
    baseTPModule_dst = os.path.join(plugin_path, 'Source', 'ThirdParty', 'BaseTPLibrary')
    print(f"copying the BaseTPModule from {baseTPModule_src} to {baseTPModule_dst}" )
    shutil.copytree(baseTPModule_src, baseTPModule_dst)

    baseClientModule_src = os.path.join('./BaseModules', 'AWSBase')
    baseClientModule_dst = os.path.join(plugin_path, 'Source',  'AWSBase')
    print(f"copying the AWSBase Module from {baseClientModule_src} to {baseClientModule_dst}")
    shutil.copytree(baseClientModule_src, baseClientModule_dst)

    #Need to generate the base build file to have the correct plugin name in it 
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template("BaseModules/AWSBaseModule.cpp")
    output = template.render(context=context)

    with open(os.path.join(baseClientModule_dst,"Private","AWSBaseModule.cpp"),'w') as fh:
        fh.write(output)
    print(f"Copying the Generated AWSBaseModule file to {os.path.join(baseClientModule_dst,'Private','AWSBaseModule.cpp')}")

    icon_src = os.path.join('./Templates', 'Resources', "Icon128.png")
    icon_dst = os.path.join(plugin_path, 'Resources', "Icon128.png")
    print(f"copying the icon from {icon_src} to {icon_dst}")
    shutil.copyfile(icon_src, icon_dst)


def copyWorktoOutput(context):
    dst = os.path.join(".", output_dir, context['plugin-name'])
    if os.path.isdir(dst):
        shutil.rmtree(dst)

    src = os.path.join(".", tmp_dir, context['plugin-name'])

    shutil.copytree(src, dst)


def CreatePlugin(context):
    template_dir = './Templates'
    loader = FileSystemLoader(template_dir)
    environment = Environment(loader=loader)

    #Step 1 
    createtempdirectory()

    #Step 2 
    makeSkeletonFolderStruct(context)

    #Step 3 
    makeTPModules(context)

    #Step 4
    generateClientTemplates(context)

    #Step 5
    generatePlugingTemplates(context)

    #Step 6
    moveBaseFiles(context)

    #Step 7
    copyWorktoOutput(context)

    #Step 8
    deletetempdirectory()


    
def validateTPModule(tp_module):
    if not type(tp_module) is dict:
        return False
    
    #TODO
    #Make a function to check actually valid aws-sdk-name
    if not "aws-sdk-name" in tp_module or not type(tp_module['aws-sdk-name']) is str:
        print(f"Not valid aws-sdk-name")
        return False
    
    if not "TPModuleName" in tp_module or not type(tp_module['TPModuleName']) is str:
        print(f"Not valid TPModuleName")
        return False

    return True


def validateClientModule(client_module):
    if not type(client_module) is dict:
        return False

    if not "client-module-name" in client_module or not type(client_module['client-module-name']) is str:
        print(f"Not valid client-module-name")
        return False

    if not "sdk" in client_module or not type(client_module['sdk']) is str:
        print(f"Not valid sdk")
        return False

    if not "sh" in client_module or not type(client_module['sh']) is str:
        print(f"Not valid sh")
        return False

    if not 'TPModules' in client_module or not type(client_module['TPModules']) is list:
        print(f"Not valid TP Modules")
        return False

    for tp_mod in client_module['TPModules']:
        if not validateTPModule(tp_mod):
            return False

    return True

def loadModulesFromFile(path):
    if not os.path.isfile(os.path.join(path)) or not path.endswith(".json"):
        print("not a valid path")
        return False

    with open(os.path.join(path)) as fh:
        loaded_json = json.load(fh)

    return loaded_json['client-modules']


def main(): 
    context = {
        'plugin-name': 'AwsDemo23',
        'description': 'A demo render of the aws plugin',
        'plugin-prefix': 'AWS',
        'sdk-prefix': 'aws-cpp-sdk-',
        'tp-module-suffix': 'TPModule',
        'binaries-path': 'H:/tmp/plugin-cleanup/CompiledSDK',
        'supported_platforms': [
            {
                'Platform':'Android',  
                'Sub-Platforms':['arm64-v8a', 'armeabi-v7a'],
                'File-Types': [
                    {
                        "file-name": (lambda name: f"lib{name}.so"),
                    }
                ]
            },  
            {
                'Platform':'Win64', 
                'Sub-Platforms':[],
                'File-Types': [
                    {
                        "file-name": (lambda name: f"{name}.dll"),
                    }, 
                    {
                        "file-name": (lambda name: f"{name}.lib"),
                    }
                ]

            }
        ],
        'tp-templates':[
            {
                'name': 'ThirdParty/Library/TemplateLibrary.Build.cs',
                'path': (lambda tp_path, tp_module: os.path.join(tp_path, f"{tp_module['TPModuleName']}.Build.cs")),
                'msg': (lambda tp_module: f"Writing the generated {tp_module['TPModuleName']}.Build.cs file")
            },
            {
                'name': 'ThirdParty/Library/Template_APL.xml',
                'path': (lambda tp_path, tp_module: os.path.join(tp_path, f"{tp_module['TPModuleName']}_APL.xml")),
                'msg': (lambda tp_module: f"Writing the generated {tp_module['TPModuleName']}_APL.xml file")
            },
        ],
        'client-templates':[
            {
                'name': 'Library/AWSName.build.cs',
                'path': (lambda name: os.path.join(f"{name}.build.cs")),
                'msg': (lambda name: f"Writing the generated {name}.build.cs file")
            },
            {
                'name': 'Library/Private/AWSNameModule.cpp',
                'path': (lambda name: os.path.join("Private", f"{name}Module.cpp")),
                'msg': (lambda name: f"Writing the generated {name}Module.cpp file")
            },
            {
                'name': 'Library/Private/AWSNamePrivatePCH.h',
                'path': (lambda name: os.path.join("Private", f"{name}PrivatePCH.h")),
                'msg': (lambda name: f"Writing the generated {name}PrivatePCH.h file")
            },
            {
                'name': 'Library/Public/AWSNameModule.h',
                'path': (lambda name: os.path.join("Public", f"{name}Module.h")),
                'msg': (lambda name: f"Writing the generated {name}Module.h file")
            },
            {
                'name': 'Library/Private/AWSNameClientObject.cpp',
                'path': (lambda name: os.path.join("Private", f"{name}ClientObject.cpp")),
                'msg': (lambda name: f"Writing the generated {name}ClientObject.cpp file")
            },
            {
                'name': 'Library/Public/AWSNameClientObject.h',
                'path': (lambda name: os.path.join("Public", f"{name}ClientObject.h")),
                'msg': (lambda name: f"Writing the generated {name}ClientObject.h file")
            },         
        ],
        'plugin-templates': [
             {
                'name': "Plugin/AwsDemo.uplugin",
                'path': (lambda name: os.path.join(f"{context['plugin-name']}.uplugin")),
                'msg': (lambda name: f"Writing the generated {context['plugin-name']}.uplugin file")
            } 
        ],
    }


    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs=1, help='Command to run', choices=["make-plugin", "make-tp-module"])
    parser.add_argument("--pluginfile", nargs=1, help='location of JSON file that describes the plugin you want to create')

    arg = parser.parse_args(sys.argv[1:])
    print(arg.command)

    if not arg.pluginfile == None:
        client_mods  = loadModulesFromFile(arg.pluginfile[0])
        context['client-modules'] = client_mods
    else:
        print("interactive mode")

    for client in context['client-modules']:
        rv = validateClientModule(client)

    CreatePlugin(context)


if __name__ == "__main__":
    main()