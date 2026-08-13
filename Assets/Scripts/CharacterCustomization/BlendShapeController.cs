using System.Collections.Generic;
using UnityEngine;

namespace CharacterCustomization
{
    /// <summary>
    /// Thin wrapper around a SkinnedMeshRenderer's blend shapes, addressed by name
    /// so higher-level systems never depend on blend shape index order.
    /// </summary>
    public class BlendShapeController : MonoBehaviour
    {
        [SerializeField] private SkinnedMeshRenderer targetRenderer;

        private Dictionary<string, int> shapeIndexByName;

        private void Awake()
        {
            CacheShapeIndices();
        }

        public void CacheShapeIndices()
        {
            shapeIndexByName = new Dictionary<string, int>();

            var mesh = targetRenderer != null ? targetRenderer.sharedMesh : null;
            if (mesh == null)
            {
                return;
            }

            for (int i = 0; i < mesh.blendShapeCount; i++)
            {
                shapeIndexByName[mesh.GetBlendShapeName(i)] = i;
            }
        }

        public bool HasShape(string shapeName)
        {
            return shapeIndexByName != null && shapeIndexByName.ContainsKey(shapeName);
        }

        public void SetWeight(string shapeName, float weight)
        {
            if (shapeIndexByName == null)
            {
                CacheShapeIndices();
            }

            if (shapeIndexByName.TryGetValue(shapeName, out int index))
            {
                targetRenderer.SetBlendShapeWeight(index, Mathf.Clamp(weight, 0f, 100f));
            }
        }

        public float GetWeight(string shapeName)
        {
            if (shapeIndexByName != null && shapeIndexByName.TryGetValue(shapeName, out int index))
            {
                return targetRenderer.GetBlendShapeWeight(index);
            }

            return 0f;
        }

        public IEnumerable<string> AvailableShapeNames => shapeIndexByName?.Keys ?? System.Array.Empty<string>();
    }
}
