using System;
using System.Collections.Generic;
using UnityEngine;

namespace CharacterCustomization
{
    public enum MorphCategory
    {
        Body,
        Face
    }

    [Serializable]
    public class MorphSlider
    {
        [Tooltip("Stable identifier used in save data and UI bindings.")]
        public string id;

        public string displayName;
        public MorphCategory category;

        [Tooltip("Blend shape name on the character's SkinnedMeshRenderer. Leave empty for a scale-driven slider like Height.")]
        public string blendShapeName;

        [Range(0f, 100f)]
        public float defaultValue = 50f;

        [Tooltip("If true, this slider drives a uniform scale on the configured scale root instead of (or in addition to) a blend shape.")]
        public bool drivesUniformScale;

        public float minScale = 0.85f;
        public float maxScale = 1.15f;
    }

    [CreateAssetMenu(menuName = "Character Customization/Morph Profile", fileName = "MorphProfile")]
    public class MorphProfile : ScriptableObject
    {
        public List<MorphSlider> sliders = new List<MorphSlider>();

        public MorphSlider Find(string sliderId)
        {
            return sliders.Find(s => s.id == sliderId);
        }
    }
}
