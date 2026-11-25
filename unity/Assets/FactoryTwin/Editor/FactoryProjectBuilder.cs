using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;

namespace Zhiyin.FactoryTwin.Editor
{
    [InitializeOnLoad]
    public static class FactoryProjectBuilder
    {
        const string ScenePath="Assets/FactoryTwin/Scenes/FactoryCampus.unity";
        static readonly string CommandPath=Path.GetFullPath("Library/factory-command.txt");
        static readonly string ResultPath=Path.GetFullPath("Library/factory-result.txt");
        static FactoryProjectBuilder(){EditorApplication.update+=Poll;}
        static void Poll()
        {
            if(EditorApplication.isCompiling||EditorApplication.isUpdating||!File.Exists(CommandPath))return;
            string command=File.ReadAllText(CommandPath).Trim();File.Delete(CommandPath);
            try
            {
                if(command=="scene"){CreateScene();File.WriteAllText(ResultPath,"SCENE_OK");}
                else if(command=="build"){BuildWindows();}
                else if(command=="play"){EditorSceneManager.OpenScene(ScenePath);EditorApplication.isPlaying=true;EditorWindow.GetWindow(typeof(EditorWindow).Assembly.GetType("UnityEditor.GameView")).Focus();File.WriteAllText(ResultPath,"PLAY_OK");}
                else if(command=="stop"){EditorApplication.isPlaying=false;File.WriteAllText(ResultPath,"STOP_OK");}
                else if(command=="refresh"){AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);File.WriteAllText(ResultPath,"REFRESH_OK");}
            }
            catch(Exception ex){File.WriteAllText(ResultPath,ex.ToString());Debug.LogException(ex);}
        }
        [MenuItem("质因云联/生成或重建仿真园区")]
        public static void CreateScene()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("请先停止播放。");
            // The initial project is backed up outside this project before generation.
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            FactoryCampusBuilder.Build();
            FactoryEnvironmentBuilder.Build();
            Directory.CreateDirectory("Assets/FactoryTwin/Generated/Materials");
            Directory.CreateDirectory("Assets/FactoryTwin/Generated/Meshes");
            const string leafPath="Assets/FactoryTwin/Generated/Materials/OriginalLeafClusters.asset";
            var leafAsset=AssetDatabase.LoadAssetAtPath<Texture2D>(leafPath);
            if(leafAsset!=null)EditorUtility.CopySerialized(FactoryVegetationBuilder.LeafTexture,leafAsset);
            else{leafAsset=FactoryVegetationBuilder.LeafTexture;AssetDatabase.CreateAsset(leafAsset,leafPath);}
            FactoryVegetationBuilder.LeafMaterial.mainTexture=leafAsset;
            var saved=new Dictionary<Material,Material>();
            foreach(var renderer in UnityEngine.Object.FindObjectsOfType<Renderer>())
            {
                var materials=renderer.sharedMaterials;
                for(int i=0;i<materials.Length;i++)materials[i]=SaveMaterial(materials[i],saved);
                renderer.sharedMaterials=materials;
            }
            // Persist procedural geometry so the saved scene and Windows build use the same landscape.
            var savedMeshes=new Dictionary<Mesh,Mesh>();
            foreach(var filter in UnityEngine.Object.FindObjectsOfType<MeshFilter>())
            {
                Mesh mesh=filter.sharedMesh;
                if(mesh==null||mesh.name=="Cube"||mesh.name=="Cylinder"||mesh.name=="Sphere"||mesh.name=="Capsule"||mesh.name=="Plane"||mesh.name=="Quad")continue;
                if(savedMeshes.ContainsKey(mesh)){filter.sharedMesh=savedMeshes[mesh];continue;}
                string path="Assets/FactoryTwin/Generated/Meshes/"+mesh.name.Replace("/","_")+".asset";
                var existing=AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if(existing!=null){EditorUtility.CopySerialized(mesh,existing);filter.sharedMesh=existing;savedMeshes[mesh]=existing;}
                else {AssetDatabase.CreateAsset(mesh,path);savedMeshes[mesh]=mesh;}
            }
            RenderSettings.skybox=SaveMaterial(RenderSettings.skybox,saved);
            var cameraObject=new GameObject("Main Camera");cameraObject.tag="MainCamera";
            var camera=cameraObject.AddComponent<Camera>();camera.fieldOfView=48;camera.nearClipPlane=.2f;camera.farClipPlane=1800;
            var background=new GameObject("Dashboard Background").AddComponent<Camera>();
            background.clearFlags=CameraClearFlags.Skybox;background.depth=-10;background.farClipPlane=1800;background.allowHDR=true;
            background.gameObject.AddComponent<FactoryBackdropCamera>().source=camera;
            // The reference camera retains the original central ray/label viewport. The full-screen
            // camera renders once, including behind panels, and gives glass a full-screen scene capture.
            camera.clearFlags=CameraClearFlags.Nothing;camera.cullingMask=0;camera.depth=-20;camera.allowHDR=true;
            camera.rect=new Rect(463f/1920f,202f/1080f,994f/1920f,708f/1080f);
            cameraObject.AddComponent<AudioListener>();var orbit=cameraObject.AddComponent<FactoryOrbitCamera>();
            cameraObject.transform.position=orbit.target+Quaternion.Euler(orbit.pitch,orbit.yaw,0)*new Vector3(0,0,-orbit.distance);cameraObject.transform.LookAt(orbit.target);
            new GameObject("Factory Application").AddComponent<FactoryTwinApp>();
            Directory.CreateDirectory("Assets/FactoryTwin/Scenes");
            EditorSceneManager.SaveScene(scene,ScenePath);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
            PlayerSettings.companyName="质因云联团队";PlayerSettings.productName="质因云联仿真工厂";PlayerSettings.bundleVersion="1.0.0";
            PlayerSettings.defaultScreenWidth=1920;PlayerSettings.defaultScreenHeight=1080;
            PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.resizableWindow=true;PlayerSettings.runInBackground=true;
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone,ScriptingImplementation.Mono2x);
            PlayerSettings.colorSpace=ColorSpace.Linear;
            QualitySettings.antiAliasing=4;QualitySettings.shadowResolution=ShadowResolution.High;QualitySettings.shadowDistance=340;QualitySettings.shadowCascades=4;
            AssetDatabase.SaveAssets();AssetDatabase.Refresh();
            Selection.activeGameObject=GameObject.Find("质因云联 · 仿真园区");
            if(SceneView.lastActiveSceneView!=null)SceneView.lastActiveSceneView.LookAt(Vector3.zero,Quaternion.Euler(43,-26,0),110);
            Debug.Log("FactoryCampus scene generated.");
        }
        static Material SaveMaterial(Material material,Dictionary<Material,Material> cache)
        {
            if(material==null)return null;if(cache.ContainsKey(material))return cache[material];
            string path="Assets/FactoryTwin/Generated/Materials/"+material.name+".mat";
            var existing=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(existing!=null){EditorUtility.CopySerialized(material,existing);cache[material]=existing;return existing;}
            AssetDatabase.CreateAsset(material,path);cache[material]=material;return material;
        }
        [MenuItem("质因云联/导出 Windows 程序")]
        public static void BuildWindows()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("请先停止播放。");
            if(!File.Exists(ScenePath))CreateScene();
            Directory.CreateDirectory("Build/Windows");
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{
                scenes=new[]{ScenePath},locationPathName="Build/Windows/质因云联仿真工厂.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.None});
            File.WriteAllText(ResultPath,"BUILD_"+report.summary.result+"\nErrors="+report.summary.totalErrors+"\nSize="+report.summary.totalSize+"\nDuration="+report.summary.totalTime);
            if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Windows build failed: "+report.summary.result);
            File.Copy("Assets/FactoryTwin/Resources/Fonts/OFL.txt","Build/Windows/字体许可证.txt",true);
            if(File.Exists("运行说明.md"))File.Copy("运行说明.md","Build/Windows/运行说明.md",true);
        }
    }
}
