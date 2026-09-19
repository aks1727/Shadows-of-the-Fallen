#if UNITY_EDITOR
using System.IO;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public class TerrainBatchImporter : EditorWindow
{
    private string basePath = "Assets/TerrainData/RawHeightmaps";
    private int selectedRegionIndex = 0;
    private string[] regionFolders = new string[0];

    // Single tile import fields
    private int singleCellX = 0;
    private int singleCellY = 0;

    [System.Serializable]
    private class RegionMeta
    {
        public string region_id;
        public int min_cx;
        public int max_cx;
        public int min_cy;
        public int max_cy;
        public float global_min_z;
        public float global_max_z;
        public float height_span;
        public int resolution;
        public float cell_size;
    }

    [MenuItem("Tools/Terrain/Region Batch Importer")]
    public static void ShowWindow()
    {
        GetWindow<TerrainBatchImporter>("Terrain Importer");
    }

    private void OnEnable()
    {
        RefreshRegionList();
    }

    private void RefreshRegionList()
    {
        if (Directory.Exists(basePath))
        {
            string[] dirs = Directory.GetDirectories(basePath);
            regionFolders = new string[dirs.Length];
            for (int i = 0; i < dirs.Length; i++)
            {
                regionFolders[i] = Path.GetFileName(dirs[i]);
            }
        }
        else
        {
            regionFolders = new string[0];
        }
    }

    private void OnGUI()
    {
        GUILayout.Label("Terrain Tile & Region Importer", EditorStyles.boldLabel);
        basePath = EditorGUILayout.TextField("Base Directory", basePath);

        if (GUILayout.Button("Refresh Region Folders"))
        {
            RefreshRegionList();
        }

        if (regionFolders.Length == 0)
        {
            EditorGUILayout.HelpBox("No region folders found under: " + basePath, MessageType.Warning);
            return;
        }

        selectedRegionIndex = EditorGUILayout.Popup("Target Region", selectedRegionIndex, regionFolders);
        string currentRegion = regionFolders[selectedRegionIndex];

        EditorGUILayout.Space(10);
        EditorGUILayout.LabelField("Single Cell Import", EditorStyles.boldLabel);
        EditorGUILayout.BeginHorizontal();
        singleCellX = EditorGUILayout.IntField("Cell X (cx)", singleCellX);
        singleCellY = EditorGUILayout.IntField("Cell Y (cy)", singleCellY);
        EditorGUILayout.EndHorizontal();

        if (GUILayout.Button($"Import Single Cell ({singleCellX:+03d}, {singleCellY:+03d})"))
        {
            ImportSingleCell(currentRegion, singleCellX, singleCellY);
        }

        EditorGUILayout.Space(15);
        EditorGUILayout.LabelField("Batch Region Import", EditorStyles.boldLabel);
        if (GUILayout.Button($"Import Entire Region: {currentRegion}", GUILayout.Height(30)))
        {
            ImportRegion(currentRegion);
        }
    }

    private RegionMeta LoadMeta(string regionName)
    {
        string metaPath = Path.Combine(basePath, regionName, "region_meta.json");
        if (!File.Exists(metaPath))
        {
            Debug.LogError($"Manifest missing at: {metaPath}");
            return null;
        }
        return JsonUtility.FromJson<RegionMeta>(File.ReadAllText(metaPath));
    }

    private GameObject GetOrCreateRegionRoot(string regionId)
    {
        string rootName = $"REGION_{regionId}";
        GameObject regionRoot = GameObject.Find(rootName);
        if (regionRoot == null)
        {
            regionRoot = new GameObject(rootName);
        }
        return regionRoot;
    }

    private Terrain BuildTerrainTile(string rawFilePath, int cx, int cy, RegionMeta meta, Transform parentRoot)
    {
        string assetDir = $"Assets/TerrainData/GeneratedData/{meta.region_id}";
        if (!Directory.Exists(assetDir)) Directory.CreateDirectory(assetDir);

        TerrainData tData = new TerrainData();
        tData.heightmapResolution = meta.resolution;
        tData.size = new Vector3(meta.cell_size, meta.height_span, meta.cell_size);

        byte[] rawBytes = File.ReadAllBytes(rawFilePath);
        float[,] heights = new float[meta.resolution, meta.resolution];

        int byteIndex = 0;
        for (int zIndex = 0; zIndex < meta.resolution; zIndex++)
        {
            for (int xIndex = 0; xIndex < meta.resolution; xIndex++)
            {
                ushort val = System.BitConverter.ToUInt16(rawBytes, byteIndex);
                heights[zIndex, xIndex] = val / 65535f;
                byteIndex += 2;
            }
        }

        tData.SetHeights(0, 0, heights);
        string assetPath = $"{assetDir}/TerrainData_{cx:+03d}_{cy:+03d}.asset";
        AssetDatabase.CreateAsset(tData, assetPath);

        string tileName = $"TERRAIN_{cx:+03d}_{cy:+03d}";
        Transform existingTile = parentRoot.Find(tileName);
        if (existingTile != null)
        {
            DestroyImmediate(existingTile.gameObject);
        }

        GameObject terrainGo = Terrain.CreateTerrainGameObject(tData);
        terrainGo.name = tileName;
        terrainGo.transform.parent = parentRoot;
        terrainGo.transform.position = new Vector3(
            cx * meta.cell_size,
            meta.global_min_z,
            cy * meta.cell_size
        );

        return terrainGo.GetComponent<Terrain>();
    }

    private void ImportSingleCell(string regionName, int cx, int cy)
    {
        RegionMeta meta = LoadMeta(regionName);
        if (meta == null) return;

        string targetDir = Path.Combine(basePath, regionName);
        string filename = $"Terrain_RAW_{cx:+03d}_{cy:+03d}.raw";
        string filePath = Path.Combine(targetDir, filename);

        if (!File.Exists(filePath))
        {
            Debug.LogError($"Heightmap not found for cell ({cx}, {cy}) at: {filePath}");
            return;
        }

        GameObject root = GetOrCreateRegionRoot(meta.region_id);
        Terrain tile = BuildTerrainTile(filePath, cx, cy, meta, root.transform);

        AssetDatabase.SaveAssets();
        StitchSurroundingNeighbors(root, cx, cy);

        Debug.Log($"[SOTF] Successfully imported single cell CELL_{cx:+03d}_{cy:+03d} into {root.name}");
    }

    private void ImportRegion(string regionName)
    {
        RegionMeta meta = LoadMeta(regionName);
        if (meta == null) return;

        string targetDir = Path.Combine(basePath, regionName);
        string rootName = $"REGION_{meta.region_id}";
        GameObject regionRoot = GameObject.Find(rootName);
        if (regionRoot != null) DestroyImmediate(regionRoot);
        regionRoot = new GameObject(rootName);

        string[] files = Directory.GetFiles(targetDir, "Terrain_RAW_*.raw");
        Regex regex = new Regex(@"Terrain_RAW_([+-]\d+)_([+-]\d+)\.raw");

        Dictionary<Vector2Int, Terrain> grid = new Dictionary<Vector2Int, Terrain>();

        foreach (string file in files)
        {
            Match match = regex.Match(Path.GetFileName(file));
            if (!match.Success) continue;

            int cx = int.Parse(match.Groups[1].Value);
            int cy = int.Parse(match.Groups[2].Value);

            Terrain t = BuildTerrainTile(file, cx, cy, meta, regionRoot.transform);
            grid[new Vector2Int(cx, cy)] = t;
        }

        AssetDatabase.SaveAssets();

        foreach (var pair in grid)
        {
            Vector2Int c = pair.Key;
            Terrain t = pair.Value;

            grid.TryGetValue(new Vector2Int(c.x - 1, c.y), out Terrain left);
            grid.TryGetValue(new Vector2Int(c.x + 1, c.y), out Terrain right);
            grid.TryGetValue(new Vector2Int(c.x, c.y + 1), out Terrain top);
            grid.TryGetValue(new Vector2Int(c.x, c.y - 1), out Terrain bottom);

            t.SetNeighbors(left, top, right, bottom);
        }

        Debug.Log($"[SOTF] Region '{meta.region_id}' imported ({grid.Count} tiles).");
    }

    private void StitchSurroundingNeighbors(GameObject root, int cx, int cy)
    {
        Terrain current = GetTerrainAt(root, cx, cy);
        if (current == null) return;

        Terrain left = GetTerrainAt(root, cx - 1, cy);
        Terrain right = GetTerrainAt(root, cx + 1, cy);
        Terrain top = GetTerrainAt(root, cx, cy + 1);
        Terrain bottom = GetTerrainAt(root, cx, cy - 1);

        current.SetNeighbors(left, top, right, bottom);

        if (left != null) left.SetNeighbors(GetTerrainAt(root, cx - 2, cy), GetTerrainAt(root, cx - 1, cy + 1), current, GetTerrainAt(root, cx - 1, cy - 1));
        if (right != null) right.SetNeighbors(current, GetTerrainAt(root, cx + 1, cy + 1), GetTerrainAt(root, cx + 2, cy), GetTerrainAt(root, cx + 1, cy - 1));
        if (top != null) top.SetNeighbors(GetTerrainAt(root, cx - 1, cy + 1), GetTerrainAt(root, cx, cy + 2), GetTerrainAt(root, cx + 1, cy + 1), current);
        if (bottom != null) bottom.SetNeighbors(GetTerrainAt(root, cx - 1, cy - 1), current, GetTerrainAt(root, cx + 1, cy - 1), GetTerrainAt(root, cx, cy - 2));
    }

    private Terrain GetTerrainAt(GameObject root, int cx, int cy)
    {
        Transform child = root.transform.Find($"TERRAIN_{cx:+03d}_{cy:+03d}");
        return child ? child.GetComponent<Terrain>() : null;
    }
}
#endif