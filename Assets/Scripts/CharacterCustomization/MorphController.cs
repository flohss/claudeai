using System.Collections.Generic;
using UnityEngine;

namespace CharacterCustomization
{
    /// <summary>
    /// Drives body and face morphology from a data-driven MorphProfile, so adding a new
    /// slider only requires editing the profile asset, not writing new code.
    /// </summary>
    public class MorphController : MonoBehaviour
    {
        [SerializeField] private BlendShapeController blendShapes;
        [SerializeField] private Transform scaleRoot;
        [SerializeField] private MorphProfile profile;

        private readonly Dictionary<string, float> currentValues = new Dictionary<string, float>();

        public MorphProfile Profile => profile;

        public void ApplyDefaults()
        {
            foreach (var slider in profile.sliders)
            {
                SetValue(slider.id, slider.defaultValue);
            }
        }

        public void SetValue(string sliderId, float weight)
        {
            var slider = profile.Find(sliderId);
            if (slider == null)
            {
                return;
            }

            weight = Mathf.Clamp(weight, 0f, 100f);
            currentValues[sliderId] = weight;

            if (!string.IsNullOrEmpty(slider.blendShapeName))
            {
                blendShapes.SetWeight(slider.blendShapeName, weight);
            }

            if (slider.drivesUniformScale && scaleRoot != null)
            {
                float t = weight / 100f;
                float scale = Mathf.Lerp(slider.minScale, slider.maxScale, t);
                scaleRoot.localScale = new Vector3(scale, scale, scale);
            }
        }

        public float GetValue(string sliderId)
        {
            return currentValues.TryGetValue(sliderId, out var value) ? value : 0f;
        }

        public IReadOnlyDictionary<string, float> GetAllValues() => currentValues;
    }
}
